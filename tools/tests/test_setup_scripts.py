#!/usr/bin/env python3
"""Offline test of tools/setup-cloud.sh and tools/inkos-agent-bridge/install.sh.

Each case runs with a temporary HOME against a temporary copy of the scripts
(tools/ only) with a fake build output, so the test needs no build and no
network. The pnpm cases put a fake installed pnpm 11 (fails on anything but
--version) and fake corepack/npx first on PATH; the fake pnpm 9.15.9 behind
corepack/npx runs nested `pnpm` calls the way the repository's package scripts do. The link cases check that a link at a target path is replaced
itself and that the bytes of the file it pointed to stay the same.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2]
results = []
root = Path(tempfile.mkdtemp(prefix="setup-scripts-test-"))
# A repository copy: the two scripts, the bridge, and a fake CLI build.
REPO = root / "repo"
(REPO / "tools").mkdir(parents=True)
shutil.copy2(SOURCE / "tools" / "setup-cloud.sh", REPO / "tools" / "setup-cloud.sh")
shutil.copytree(SOURCE / "tools" / "inkos-agent-bridge", REPO / "tools" / "inkos-agent-bridge", symlinks=True,
                ignore=shutil.ignore_patterns("runtime", "__pycache__", "tests"))
if (SOURCE / "tools" / "pnpm-pin").is_dir():
    shutil.copytree(SOURCE / "tools" / "pnpm-pin", REPO / "tools" / "pnpm-pin")
(REPO / "packages" / "cli").mkdir(parents=True)
(REPO / "packages" / "cli" / "dist").mkdir(parents=True)
(REPO / "packages" / "cli" / "dist" / "index.js").write_text("console.log('2.0.0 (fake build for setup tests)');\n")
SETUP = REPO / "tools" / "setup-cloud.sh"
INSTALL = REPO / "tools" / "inkos-agent-bridge" / "install.sh"
AGENT_TARGET = REPO / "tools" / "inkos-agent-bridge" / "inkos-agent"
MARK = "# inkos-ko setup"


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
bashrc = (home / ".bashrc").read_text() if (home / ".bashrc").exists() else ""
check("~/.bashrc gets exactly two lines", bashrc.splitlines()[:1] == [MARK] and len(bashrc.splitlines()) == 2
      and f'INKOS_AGENT_PROJECT="{project}"' in bashrc, bashrc)
gi = (project / ".gitignore").read_text().splitlines() if (project / ".gitignore").exists() else []
check("project .gitignore lists runtime/ and inkos.pre-agent.json", gi == ["runtime/", "inkos.pre-agent.json"], gi)
r = run(SETUP, env, "--project", str(project), "--no-build")
check("rerun of the same setup is not an 'existing installation'", r.returncode == 0, r.stdout + r.stderr)
check("rerun keeps one ~/.bashrc block", (home / ".bashrc").read_text() == bashrc)
check("rerun leaves no backup", not (bin_ / ".inkos-ko-backup").exists())

# ---------- 1a. permissions of ~/.bashrc and the project .gitignore are kept ----------
base, home, project, fake, env = case("modes")
(home / ".bashrc").write_text('alias ll="ls -l"\n')
(home / ".bashrc").chmod(0o600)
(project / ".gitignore").write_text("node_modules/\n")
(project / ".gitignore").chmod(0o640)
r = run(SETUP, env, "--project", str(project), "--no-build")
check("~/.bashrc keeps mode 600", r.returncode == 0 and oct((home / ".bashrc").stat().st_mode & 0o777) == "0o600",
      oct((home / ".bashrc").stat().st_mode & 0o777))
check("project .gitignore keeps mode 640", oct((project / ".gitignore").stat().st_mode & 0o777) == "0o640",
      oct((project / ".gitignore").stat().st_mode & 0o777))

# ---------- 1b. ~/.bashrc is a link (dotfiles manager): left alone, lines printed ----------
base, home, project, fake, env = case("bashrc-link")
dot_rc = base / "other" / "dotfiles-bashrc"
dot_bytes = decoy(dot_rc, 'alias ll="ls -l"\n')
(home / ".bashrc").symlink_to(dot_rc)
r = run(SETUP, env, "--project", str(project), "--no-build")
check("linked ~/.bashrc: setup continues (exit 0)", r.returncode == 0, r.stdout + r.stderr)
check("linked ~/.bashrc: link and its target unchanged",
      os.readlink(home / ".bashrc") == str(dot_rc) and dot_rc.read_bytes() == dot_bytes)
check("linked ~/.bashrc: the two lines are printed to add by hand",
      "a link, left unchanged" in r.stdout and f"{MARK}\nexport PATH=" in r.stdout and f'INKOS_AGENT_PROJECT="{project}"' in r.stdout, r.stdout)
check("linked ~/.bashrc: the rest is installed", (home / ".local/bin/inkos").is_file()
      and os.readlink(home / ".local/bin/inkos-agent") == str(AGENT_TARGET))

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
check("two foreign items listed before --replace (a linked ~/.bashrc is not one)",
      r.returncode == 3 and r.stderr.count(" -> ") == 2 and ".bashrc" not in r.stderr, r.stderr)
r = run(SETUP, env, "--project", str(project), "--no-build", "--replace")
check("--replace succeeds", r.returncode == 0, r.stdout + r.stderr)
check("--replace: link targets' bytes unchanged",
      other_js.read_bytes() == other_bytes and other_agent.read_bytes() == agent_bytes and other_rc.read_bytes() == rc_bytes)
check("--replace: inkos is now our launcher file", not (bin_ / "inkos").is_symlink() and (bin_ / "inkos").read_text() == launcher())
check("--replace: inkos-agent links to this bridge", os.readlink(bin_ / "inkos-agent") == str(AGENT_TARGET))
rc_now = home / ".bashrc"
check("--replace: a linked ~/.bashrc stays a link", os.readlink(rc_now) == str(other_rc))
backups = sorted((bin_ / ".inkos-ko-backup").iterdir())
check("one backup directory", len(backups) == 1, backups)
b = backups[0]
check("backup keeps the original links", os.readlink(b / "inkos") == str(other_js) and os.readlink(b / "inkos-agent") == str(other_agent)
      and not (b / "bashrc").exists())
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
      and (project / "AGENTS.md").read_bytes() == (SOURCE / "tools/inkos-agent-bridge/AGENTS.md").read_bytes())
check("install.sh: .gitignore keeps old lines and adds two",
      (project / ".gitignore").read_text().splitlines() == ["node_modules/", "runtime/", "inkos.pre-agent.json"])
b = next((bin_ / ".inkos-ko-backup").iterdir())
subprocess.run(["sh", str(b / "restore.sh")], env=env, check=True)
check("install.sh restore.sh brings the old inkos-agent link back", os.readlink(bin_ / "inkos-agent") == str(other_agent))

# ---------- 8. pnpm pinned to 9.15.9, nested calls included ----------
def pinned_pnpm(who, log):
    """A fake pnpm 9.15.9 that makes the nested calls the real package scripts make."""
    return (f'echo "{who} $*" >> "{log}"\n'
            'case "$*" in\n'
            '  *--version*) echo 9.15.9 ;;\n'
            # pnpm -r build: packages/cli prebuild runs `pnpm run prepare:workspace-core` (pnpm found on PATH)
            f'  *"-r build"*) (cd "{REPO}/packages/cli" && pnpm run prepare:workspace-core) || exit 1 ;;\n'
            '  *"run prepare:workspace-core"*) pnpm --filter @actalk/inkos-core build || exit 1 ;;\n'
            # pnpm -r test: packages/cli pretest runs `pnpm run build`
            f'  *"-r --no-bail test"*) (cd "{REPO}/packages/cli" && pnpm run build) || exit 1 ;;\n'
            '  *"run build"*) pnpm run prepare:workspace-core || exit 1 ;;\n'
            'esac\nexit 0\n')


def pnpm_case(name, installed_ok, corepack_ok):
    base, home, project, fake, env = case(name)
    log = base / "calls.log"
    if installed_ok:
        fake_cmd(fake, "pnpm", pinned_pnpm("pnpm9", log))
    else:  # the installed pnpm 11: any real use fails, like ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY
        fake_cmd(fake, "pnpm", f'echo "pnpm11 $*" >> "{log}"\n[ "$1" = --version ] && {{ echo 11.25.0; exit 0; }}\n'
                               'echo "fake pnpm 11 must not run: $*" >&2\nexit 1\n')
    fake_cmd(fake, "corepack", pinned_pnpm("corepack", log) if corepack_ok else f'echo "corepack $*" >> "{log}"\nexit 1\n')
    fake_cmd(fake, "npx", pinned_pnpm("npx", log))
    r = run(SETUP, env, "--project", str(project))
    test = subprocess.run(["sh", "-c", f'cd "{REPO}" && PATH="$PWD/tools/pnpm-pin:$PATH" pnpm -r --no-bail test'],
                          env=env, capture_output=True, text=True)
    calls = log.read_text().splitlines() if log.exists() else []
    return r, test, calls


def pnpm11_work(calls):
    return [c for c in calls if c.startswith("pnpm11 ") and c != "pnpm11 --version"]


r, test, calls = pnpm_case("pnpm-corepack", False, True)
check("pnpm 11 installed: corepack pnpm@9.15.9 is used",
      r.returncode == 0 and "pnpm: 9.15.9 via 'corepack pnpm@9.15.9' (installed pnpm: 11.25.0)" in r.stdout, r.stdout + r.stderr)
check("install (no purge prompt) and build ran through corepack",
      "corepack pnpm@9.15.9 install --frozen-lockfile --config.confirm-modules-purge=false" in calls
      and "corepack pnpm@9.15.9 -r build" in calls, calls)
check("nested calls from package scripts also went through corepack",
      "corepack pnpm@9.15.9 run prepare:workspace-core" in calls
      and "corepack pnpm@9.15.9 --filter @actalk/inkos-core build" in calls, calls)
check("the documented test command pins nested calls too",
      test.returncode == 0 and "corepack pnpm@9.15.9 -r --no-bail test" in calls and "corepack pnpm@9.15.9 run build" in calls,
      test.stdout + test.stderr + str(calls))
check("fake pnpm 11 was never run for work (only --version)", not pnpm11_work(calls), pnpm11_work(calls))
local_bin = root / "pnpm-corepack" / "home" / ".local" / "bin"
check("no pnpm placed in ~/.local/bin or ~/.bashrc", sorted(p.name for p in local_bin.iterdir()) == ["inkos", "inkos-agent"]
      and "pnpm-pin" not in (root / "pnpm-corepack" / "home" / ".bashrc").read_text(), sorted(p.name for p in local_bin.iterdir()))

r, test, calls = pnpm_case("pnpm-npx", False, False)
check("no working corepack: npx -y pnpm@9.15.9 is used, nested calls included",
      r.returncode == 0 and "pnpm: 9.15.9 via 'npx -y pnpm@9.15.9' (installed pnpm: 11.25.0)" in r.stdout
      and "npx -y pnpm@9.15.9 -r build" in calls and "npx -y pnpm@9.15.9 --filter @actalk/inkos-core build" in calls
      and not pnpm11_work(calls), r.stdout + r.stderr + str(calls))

r, test, calls = pnpm_case("pnpm-ok", True, True)
real = root / "pnpm-ok" / "fakebin" / "pnpm"
check("pnpm 9.15.9 installed: used directly, nested calls included",
      r.returncode == 0 and f"pnpm: 9.15.9 via '{real}'" in r.stdout and "pnpm9 -r build" in calls
      and "pnpm9 --filter @actalk/inkos-core build" in calls
      and not [c for c in calls if c.startswith(("corepack", "npx"))], r.stdout + str(calls))

# The shim never picks itself, even when a copy of it sits on PATH (no recursion).
base, home, project, fake, env = case("pnpm-self")
shutil.copy2(REPO / "tools" / "pnpm-pin" / "pnpm", fake / "pnpm")
log = base / "calls.log"
fake_cmd(fake, "corepack", pinned_pnpm("corepack", log))
r = subprocess.run(["sh", "-c", f'PATH="{REPO}/tools/pnpm-pin:$PATH" pnpm -r build'], env=env, capture_output=True, text=True, timeout=60)
check("a copy of the shim on PATH is skipped, not recursed into", r.returncode == 0 and "corepack pnpm@9.15.9 -r build" in log.read_text(),
      r.stdout + r.stderr)
r = subprocess.run(["sh", str(REPO / "tools" / "pnpm-pin" / "pnpm"), "--version"], env={**env, "INKOS_PNPM_PIN_DEPTH": "21"},
                   capture_output=True, text=True)
check("a runaway nesting stops (exit 70)", r.returncode == 70 and "refusing" in r.stderr, r.stderr)

shutil.rmtree(root, ignore_errors=True)
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
