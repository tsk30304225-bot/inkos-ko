#!/usr/bin/env python3
"""Slow check (~6 min): answers arrive after Node fetch's default 300 s body/header
timeouts, with production keepalive settings. Proves the keepalive actually works."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE.parent / "inkos_agent.py"
tmp = Path(tempfile.mkdtemp(prefix="inkos-agent-long-"))
(tmp / "project").mkdir()
(tmp / "project" / "inkos.json").write_text("{}")
DELAY = float(os.environ.get("LONG_WAIT_S", "330"))
ENV = {**os.environ, "INKOS_AGENT_STATE": str(tmp / "state"), "INKOS_AGENT_PORT": str(47000 + os.getpid() % 1000),
       "INKOS_BIN": str(HERE / "fake_inkos.mjs"), "INKOS_AGENT_PROJECT": str(tmp / "project")}


def cli(*args):
    return subprocess.run([sys.executable, "-I", str(CLI), *args], env=ENV, capture_output=True, text=True, check=True).stdout


cli("start")
try:
    jobs = {mode: cli("job", "start", "--", mode).strip() for mode in ("stream", "buffered")}
    time.sleep(3)
    pending = [line.split()[0] for line in cli("pending").splitlines() if line.startswith("r-")]
    assert len(pending) == 2, pending
    print(f"waiting {DELAY:.0f}s before answering {pending}", flush=True)
    time.sleep(DELAY)
    for rid in pending:
        cli("reply", rid, "--text", f"{DELAY:.0f}초 뒤의 답")
    ok = True
    for mode, jid in jobs.items():
        end = time.time() + 60
        while not (tmp / "state" / "jobs" / f"{jid}.exit").exists() and time.time() < end:
            time.sleep(1)
        last = (tmp / "state" / "jobs" / f"{jid}.log").read_text().strip().splitlines()[-1]
        result = json.loads(last) if last.startswith("{") else {"raw": last}
        text = result.get("content") or (result.get("message") or {}).get("content")
        passed = text == f"{DELAY:.0f}초 뒤의 답"
        ok &= passed
        print(("PASS " if passed else "FAIL ") + f"{mode} answered after {DELAY:.0f}s: {result}")
finally:
    cli("stop")
sys.exit(0 if ok else 1)
