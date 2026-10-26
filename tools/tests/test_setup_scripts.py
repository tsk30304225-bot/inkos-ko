#!/usr/bin/env python3
"""Offline test of tools/setup-cloud.sh and tools/inkos-agent-bridge/install.sh.

Each case runs with a temporary HOME. Nothing is built or downloaded: the pnpm
cases put fake pnpm/corepack/npx scripts first on PATH and only record how they
were called. The link cases check that a link at a target path is replaced
itself and that the bytes of the file it pointed to stay the same.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SETUP = REPO / "tools" / "setup-cloud.sh"
INSTALL = REPO / "tools" / "inkos-agent-bridge" / "install.sh"
AGENT_TARGET = REPO / "tools" / "inkos-agent-bridge" / "inkos-agent"
MARK = "# inkos-ko setup"
results = []
root = Path(tempfile.mkdtemp(prefix="setup-scripts-test-"))


def check(name, condition, detail=""):
    results.append(bool(condition))
    print(("PASS " if condition else "FAIL ") + name + (f" — {detail}" if detail and not condition else ""))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return str(s.getsockname()[1])


def case(name):
    """A fresh HOME, project (already initialised, so no `inkos init`) and fake-bin dir."""
    base = root / name
    home, project, fake = base / "home", base / "project", base / "fakebin"
    for d in (home, project, fake, base / "other"):
        d.mkdir(parents=True)
    (project / "inkos.json").write_text("{}\n")
    path = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p and ".local/bin" not in p]
    env = {k: v for k, v in os.environ.items() if not k.startswith("INKOS_")}
    env.update(HOME=str(home), PATH=os.pathsep.join([str(fake), *path]),
               INKOS_AGENT_PORT=free_port(), INKOS_AGENT_STATE=str(base / "state"))
    return base, home, project, fake, env


def run(script, env, *args):
    return subprocess.run(["sh", str(script), *args], env=env, capture_output=True, text=True)


def decoy(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode())
    return path.read_bytes()


def fake_cmd(fake, name, body):
    p = fake / name
    p.write_text("#!/bin/sh\n" + body)
    p.chmod(0o755)


def launcher():
    return f'#!/bin/sh\nexec node "{REPO}/packages/cli/dist/index.js" "$@"\n'


# ---------- 1. fresh install, then a rerun of the same setup ----------
base, home, project, fake, env = case("fresh")
r = run(SETUP, env, "--project", str(project), "--no-build")
bin_ = home / ".local" / "bin"
check("fresh install succeeds", r.returncode == 0, r.stdout + r.stderr)
check("inkos launcher is a plain file", not (bin_ / "inkos").is_symlink() and (bin_ / "inkos").read_text() == launcher())
check("inkos-agent links to this bridge", os.readlink(bin_ / "inkos-agent") == str(AGENT_TARGET))
bashrc = (home / ".bashrc").read_text()
check("~/.bashrc gets exactly two lines", bashrc.splitlines()[0] == MARK and len(bashrc.splitlines()) == 2
      and f'INKOS_AGENT_PROJECT="{project}"' in bashrc, bashrc)
gi = (project / ".gitignore").read_text().splitlines()
check("project .gitignore lists runtime/ and inkos.pre-agent.json", gi == ["runtime/", "inkos.pre-agent.json"], gi)
r = run(SETUP, env, "--project", str(project), "--no-build")
check("rerun of the same setup is not an 'existing installation'", r.returncode == 0, r.stdout + r.stderr)
check("rerun keeps one ~/.bashrc block", (home / ".bashrc").read_text() == bashrc)
check("rerun leaves no backup", not (bin_ / ".inkos-ko-backup").exists())

# ---------- 2. inkos is a link into another clone: stop, change nothing ----------
base, home, project, fake, env = case("foreign-inkos")
bin_ = home / ".local" / "bin"
other_js = base / "other" / "packages" / "cli" / "dist" / "index.js"
other_bytes = decoy(other_js, "// another clone's CLI\nconsole.log('other');\n")
bin_.mkdir(parents=True)
(bin_ / "inkos").symlink_to(other_js)
r = run(SETUP, env, "--project", str(project), "--no-build")
check("foreign inkos link stops setup with exit 3", r.returncode == 3, r.stdout + r.stderr)
check("message shows where the link points", f"{bin_ / 'inkos'} -> {other_js}" in r.stderr and "--replace" in r.stderr, r.stderr)
check("link target bytes unchanged", other_js.read_bytes() == other_bytes)
check("link itself unchanged", os.readlink(bin_ / "inkos") == str(other_js))
check("nothing else written (no inkos-agent, ~/.bashrc, project files)",
      not (bin_ / "inkos-agent").exists() and not (home / ".bashrc").exists() and not (project / "AGENTS.md").exists())

# ---------- 3. only inkos-agent belongs to another install: inkos is not touched either ----------
base, home, project, fake, env = case("foreign-agent")
bin_ = home / ".local" / "bin"
other_agent = base / "other" / "inkos-agent"
agent_bytes = decoy(other_agent, "#!/bin/sh\necho other bridge\n")
bin_.mkdir(parents=True)
(bin_ / "inkos-agent").symlink_to(other_agent)
r = run(SETUP, env, "--project", str(project), "--no-build")
check("foreign inkos-agent stops setup with exit 3", r.returncode == 3 and f"-> {other_agent}" in r.stderr, r.stderr)
check("inkos is not created when only inkos-agent is foreign", not (bin_ / "inkos").exists())
check("other inkos-agent bytes unchanged", other_agent.read_bytes() == agent_bytes)

# ---------- 4. another clone's block in ~/.bashrc ----------
base, home, project, fake, env = case("foreign-block")
(home / ".bashrc").write_text(f'alias ll="ls -l"\n{MARK}\nexport PATH="/x:$PATH" INKOS_AGENT_PROJECT="/elsewhere/novel"\n')
before = (home / ".bashrc").read_bytes()
r = run(SETUP, env, "--project", str(project), "--no-build")
check("another inkos-ko block in ~/.bashrc stops setup with exit 3",
      r.returncode == 3 and "/elsewhere/novel" in r.stderr, r.stderr)
check("~/.bashrc unchanged", (home / ".bashrc").read_bytes() == before)

# ---------- 5. --replace: links replaced, targets untouched, backup restores ----------
base, home, project, fake, env = case("replace")
bin_ = home / ".local" / "bin"
other_js = base / "other" / "index.js"
other_bytes = decoy(other_js, "// other CLI\n")
other_agent = base / "other" / "inkos-agent"
agent_bytes = decoy(other_agent, "#!/bin/sh\necho other\n")
other_rc = base / "other" / "bashrc"
rc_bytes = decoy(other_rc, 'alias ll="ls -l"\n')
bin_.mkdir(parents=True)
(bin_ / "inkos").symlink_to(other_js)
(bin_ / "inkos-agent").symlink_to(other_agent)
(home / ".bashrc").symlink_to(other_rc)
r = run(SETUP, env, "--project", str(project), "--no-build")
check("three foreign items listed before --replace", r.returncode == 3 and r.stderr.count(" -> ") == 3, r.stderr)
r = run(SETUP, env, "--project", str(project), "--no-build", "--replace")
check("--replace succeeds", r.returncode == 0, r.stdout + r.stderr)
check("--replace: link targets' bytes unchanged",
      other_js.read_bytes() == other_bytes and other_agent.read_bytes() == agent_bytes and other_rc.read_bytes() == rc_bytes)
check("--replace: inkos is now our launcher file", not (bin_ / "inkos").is_symlink() and (bin_ / "inkos").read_text() == launcher())
check("--replace: inkos-agent links to this bridge", os.readlink(bin_ / "inkos-agent") == str(AGENT_TARGET))
rc_now = home / ".bashrc"
check("--replace: ~/.bashrc is a file with the old lines plus the block",
      not rc_now.is_symlink() and rc_now.read_text().startswith('alias ll="ls -l"\n' + MARK + "\n"), rc_now.read_text())
backups = sorted((bin_ / ".inkos-ko-backup").iterdir())
check("one backup directory", len(backups) == 1, backups)
b = backups[0]
check("backup keeps the original links", os.readlink(b / "inkos") == str(other_js) and os.readlink(b / "inkos-agent") == str(other_agent)
      and os.readlink(b / "bashrc") == str(other_rc))
check("backup has README and restore.sh", (b / "README").is_file() and (b / "restore.sh").is_file()
      and f"undo: sh {b}/restore.sh" in r.stdout, r.stdout)
check("install.sh used the same backup (no second backup dir)", len(list((bin_ / ".inkos-ko-backup").iterdir())) == 1)
rr = subprocess.run(["sh", str(b / "restore.sh")], env=env, capture_output=True, text=True)
check("restore.sh runs", rr.returncode == 0, rr.stdout + rr.stderr)
check("restore.sh puts the original links back", os.readlink(bin_ / "inkos") == str(other_js)
      and os.readlink(bin_ / "inkos-agent") == str(other_agent) and os.readlink(home / ".bashrc") == str(other_rc))
check("after restore, target bytes still unchanged",
      other_js.read_bytes() == other_bytes and other_agent.read_bytes() == agent_bytes and other_rc.read_bytes() == rc_bytes)

# ---------- 6. --replace when an item was absent: restore removes what setup added ----------
base, home, project, fake, env = case("replace-absent")
bin_ = home / ".local" / "bin"
other_agent = base / "other" / "inkos-agent"
decoy(other_agent, "#!/bin/sh\n")
bin_.mkdir(parents=True)
(bin_ / "inkos-agent").symlink_to(other_agent)
r = run(SETUP, env, "--project", str(project), "--no-build", "--replace")
b = next((bin_ / ".inkos-ko-backup").iterdir())
subprocess.run(["sh", str(b / "restore.sh")], env=env, check=True)
check("restore removes an inkos launcher that did not exist before",
      r.returncode == 0 and not (bin_ / "inkos").exists() and os.readlink(bin_ / "inkos-agent") == str(other_agent), r.stderr)
check("restore removes a ~/.bashrc that did not exist before", not (home / ".bashrc").exists())

# ---------- 7. install.sh alone: links in ~/.local/bin and in the project ----------
base, home, project, fake, env = case("install")
bin_ = home / ".local" / "bin"
other_agent = base / "other" / "inkos-agent"
agent_bytes = decoy(other_agent, "#!/bin/sh\necho other\n")
bin_.mkdir(parents=True)
(bin_ / "inkos-agent").symlink_to(other_agent)
r = run(INSTALL, env, "--project", str(project))
check("install.sh: foreign inkos-agent -> exit 3", r.returncode == 3 and f"-> {other_agent}" in r.stderr, r.stderr)
check("install.sh: nothing written to the project", not (project / "AGENTS.md").exists() and not (project / ".gitignore").exists())
other_doc = base / "other" / "AGENTS.md"
doc_bytes = decoy(other_doc, "# another project's AGENTS.md\n")
other_gi = base / "other" / "gitignore"
gi_bytes = decoy(other_gi, "node_modules/\n")
(project / "AGENTS.md").symlink_to(other_doc)
(project / ".gitignore").symlink_to(other_gi)
r = run(INSTALL, env, "--project", str(project), "--replace", "--force")
check("install.sh --replace succeeds", r.returncode == 0, r.stdout + r.stderr)
check("install.sh: link targets' bytes unchanged", other_agent.read_bytes() == agent_bytes
      and other_doc.read_bytes() == doc_bytes and other_gi.read_bytes() == gi_bytes)
check("install.sh: project links became files", not (project / "AGENTS.md").is_symlink()
      and (project / "AGENTS.md").read_bytes() == (REPO / "tools/inkos-agent-bridge/AGENTS.md").read_bytes())
check("install.sh: .gitignore keeps old lines and adds two",
      (project / ".gitignore").read_text().splitlines() == ["node_modules/", "runtime/", "inkos.pre-agent.json"])
b = next((bin_ / ".inkos-ko-backup").iterdir())
subprocess.run(["sh", str(b / "restore.sh")], env=env, check=True)
check("install.sh restore.sh brings the old inkos-agent link back", os.readlink(bin_ / "inkos-agent") == str(other_agent))

# ---------- 8. pnpm pinned to 9.15.9 ----------
def pnpm_case(name, installed, corepack_ok):
    base, home, project, fake, env = case(name)
    log = base / "calls.log"
    fake_cmd(fake, "pnpm", f'echo "pnpm $*" >> "{log}"\n[ "$1" = --version ] && echo {installed}\nexit 0\n')
    fake_cmd(fake, "corepack", f'echo "corepack $*" >> "{log}"\n' + (
        'case "$*" in *--version*) echo 9.15.9 ;; esac\nexit 0\n' if corepack_ok else "exit 1\n"))
    fake_cmd(fake, "npx", f'echo "npx $*" >> "{log}"\ncase "$*" in *--version*) echo 9.15.9 ;; esac\nexit 0\n')
    r = run(SETUP, env, "--project", str(project))
    calls = log.read_text().splitlines() if log.exists() else []
    return r, calls


r, calls = pnpm_case("pnpm-corepack", "11.0.0", True)
check("pnpm 11.x installed: corepack pnpm@9.15.9 is used",
      r.returncode == 0 and "pnpm: 9.15.9 via 'corepack pnpm@9.15.9' (installed pnpm: 11.0.0)" in r.stdout, r.stdout + r.stderr)
check("install and build ran through corepack, not the installed pnpm",
      "corepack pnpm@9.15.9 install --frozen-lockfile" in calls and "corepack pnpm@9.15.9 -r build" in calls
      and not [c for c in calls if c.startswith("pnpm ") and c != "pnpm --version"], calls)

r, calls = pnpm_case("pnpm-npx", "11.0.0", False)
check("no working corepack: npx -y pnpm@9.15.9 is used",
      r.returncode == 0 and "pnpm: 9.15.9 via 'npx -y pnpm@9.15.9' (installed pnpm: 11.0.0)" in r.stdout
      and "npx -y pnpm@9.15.9 install --frozen-lockfile" in calls and "npx -y pnpm@9.15.9 -r build" in calls,
      r.stdout + r.stderr + str(calls))

r, calls = pnpm_case("pnpm-ok", "9.15.9", True)
check("pnpm 9.15.9 installed: used directly",
      r.returncode == 0 and "pnpm: 9.15.9 via 'pnpm'" in r.stdout and "pnpm install --frozen-lockfile" in calls
      and not [c for c in calls if c.startswith(("corepack", "npx"))], r.stdout + str(calls))

shutil.rmtree(root, ignore_errors=True)
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
