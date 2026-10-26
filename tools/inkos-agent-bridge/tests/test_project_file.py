#!/usr/bin/env python3
"""Project and inkos binary without shell variables (Codex opens a new shell per command).

Setup runs once in a full shell (install.sh --project records the project in
runtime/project). Every later command runs like `env -i HOME=... PATH=/usr/bin:/bin`
from the repository root, which has no inkos.json. INKOS_AGENT_PORT is the only
extra variable, so the test does not touch a bridge already on 4568.
"""
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
results = []
tmp = Path(tempfile.mkdtemp(prefix="inkos-agent-project-test-"))
bridge = tmp / "bridge"
shutil.copytree(HERE.parent, bridge, symlinks=True, ignore=shutil.ignore_patterns("runtime", "__pycache__", "tests"))
home, repo, novel = tmp / "home", tmp / "repo", tmp / "novel"
for d in (home / ".local" / "bin", repo, novel):
    d.mkdir(parents=True)
(novel / "inkos.json").write_text(json.dumps({"name": "novel", "language": "ko"}))
# The setup launcher stands in for InkOS: it prints where and how it was run.
fake = home / ".local" / "bin" / "inkos"
fake.write_text('#!/bin/sh\n[ "$1" = --version ] && { echo 2.0.0; exit 0; }\n'
                'echo "fake-inkos cwd=$(pwd) args=$*"\necho "fake-inkos locale=${INKOS_LOCALE:-}"\n')
fake.chmod(0o755)
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = str(s.getsockname()[1])
BARE = {"HOME": str(home), "PATH": "/usr/bin:/bin", "INKOS_AGENT_PORT": port}
AGENT = home / ".local" / "bin" / "inkos-agent"
JOBS = bridge / "runtime" / "jobs"


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (f"  -- {detail}" if detail and not cond else ""))


def bare(*args, extra=None):
    return subprocess.run([str(AGENT), *args], cwd=repo, env={**BARE, **(extra or {})},
                          capture_output=True, text=True, encoding="utf-8", timeout=60)


def job_files():
    return sorted(p.name for p in JOBS.glob("*")) if JOBS.exists() else []


def job_log(jid):
    end = time.time() + 30
    while time.time() < end:
        if (JOBS / f"{jid}.exit").exists():
            return (JOBS / f"{jid}.log").read_text(encoding="utf-8")
        time.sleep(0.2)
    raise AssertionError(f"job {jid} did not finish")


# Setup, once, in a full shell (node on PATH) with this HOME.
full = {**os.environ, "HOME": str(home)}
full.pop("INKOS_AGENT_PROJECT", None)
full.pop("INKOS_AGENT_STATE", None)
r = subprocess.run(["sh", str(bridge / "install.sh"), "--project", str(novel), "--locale", "ko"], env=full, capture_output=True, text=True)
recorded = bridge / "runtime" / "project"
locale_file = bridge / "runtime" / "locale"
check("install.sh --project records the project in runtime/project",
      r.returncode == 0 and recorded.read_text(encoding="utf-8").strip() == str(novel.resolve()), r.stdout + r.stderr)
check("install.sh --locale ko records the locale in runtime/locale", locale_file.read_text(encoding="utf-8").strip() == "ko")
bad = subprocess.run(["sh", str(bridge / "install.sh"), "--project", str(tmp / "never"), "--locale", "k o"], env=full,
                     capture_output=True, text=True)
check("an invalid --locale stops before anything is written", bad.returncode == 2 and not (tmp / "never").exists(), bad.stderr)

try:
    # 1. record present: commands from the repository root use the recorded project
    r = bare("doctor")
    check("doctor: project from runtime/project, inkos from ~/.local/bin", r.returncode in (0, 1)
          and f"project      : {novel.resolve()} (ok, from {recorded})" in r.stdout
          and f"inkos binary : {fake} (2.0.0)" in r.stdout
          and f"locale       : ko (from {locale_file})" in r.stdout, r.stdout + r.stderr)
    r = bare("start")
    check("start with the record", r.returncode == 0 and "bridge ready" in r.stdout, r.stdout + r.stderr)
    r = bare("job", "start", "--", "status")
    jid = r.stdout.strip()
    check("job start -- status with the record", r.returncode == 0 and jid.startswith("j-"), r.stdout + r.stderr)
    if jid.startswith("j-"):
        log = job_log(jid)
        check("the job ran inkos status in the recorded project", f"fake-inkos cwd={novel.resolve()} args=status" in log, log)
        check("the job got INKOS_LOCALE=ko from runtime/locale", "fake-inkos locale=ko\n" in log, log)
        meta = json.loads((JOBS / f"{jid}.json").read_text(encoding="utf-8"))
        check("job record names the recorded project", meta["project"] == str(novel.resolve()), meta)
    r = bare("run", "--", "status")
    check("run -- status with the record", r.returncode == 0 and f"fake-inkos cwd={novel.resolve()} args=status" in r.stdout, r.stdout + r.stderr)
    other = tmp / "other"
    (other).mkdir()
    (other / "inkos.json").write_text("{}")
    r = bare("run", "--", "status", extra={"INKOS_AGENT_PROJECT": str(other)})
    check("INKOS_AGENT_PROJECT still comes first", f"fake-inkos cwd={other.resolve()}" in r.stdout, r.stdout + r.stderr)
    r = bare("run", "--", "status", extra={"INKOS_LOCALE": "en"})
    check("INKOS_LOCALE in the shell comes first", "fake-inkos locale=en\n" in r.stdout, r.stdout + r.stderr)
    locale_file.unlink()
    r = bare("run", "--", "status")
    check("without runtime/locale nothing is added (CLI falls back to LANG, then zh)", "fake-inkos locale=\n" in r.stdout, r.stdout + r.stderr)

    # 2. record absent: the repository root has no inkos.json -> exit 3, no job
    recorded.unlink()
    before = job_files()
    r = bare("job", "start", "--", "status")
    check("job start without the record: exit 3", r.returncode == 3 and "프로젝트를 찾지 못함" in r.stderr
          and str(repo.resolve()) in r.stderr and "시도한 곳" in r.stderr and f"{recorded}=(없음)" in r.stderr, r.stdout + r.stderr)
    check("job start without the record: no job created", job_files() == before, job_files())
    for args in (("run", "--", "status"), ("doctor",), ("start",)):
        r = bare(*args)
        check(f"{args[0]} without the record: exit 3", r.returncode == 3 and "프로젝트를 찾지 못함" in r.stderr, r.stdout + r.stderr)
    check("nothing ran inkos in the repository root", f"cwd={repo.resolve()}" not in "".join(
        (JOBS / name).read_text(encoding="utf-8") for name in job_files() if name.endswith(".log")))
finally:
    bare("stop")

print(f"\n{sum(results)}/{len(results)} passed")
shutil.rmtree(tmp, ignore_errors=True)
raise SystemExit(0 if all(results) else 1)
