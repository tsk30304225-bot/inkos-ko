#!/usr/bin/env python3
"""End-to-end check of the bridge with a fake inkos binary (no network, no API)."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE.parent / "inkos_agent.py"
tmp = Path(tempfile.mkdtemp(prefix="inkos-agent-test-"))
PORT = str(46000 + os.getpid() % 1000)
ENV = {**os.environ, "INKOS_AGENT_STATE": str(tmp / "state"), "INKOS_AGENT_PORT": PORT,
       "INKOS_AGENT_HEADER_GRACE_S": "1", "INKOS_AGENT_KEEPALIVE_S": "1",
       "INKOS_BIN": str(HERE / "fake_inkos.mjs"), "HTTPS_PROXY": "http://proxy.invalid:9",
       "INKOS_AGENT_PROJECT": str(tmp / "project")}
(tmp / "project").mkdir()
(tmp / "project" / "inkos.json").write_text(json.dumps({"name": "t", "llm": {"provider": "openai", "baseUrl": "https://api.example.com/v1", "model": "real"}}))
os.chmod(HERE / "fake_inkos.mjs", 0o755)
results = []


def cli(*args, check=True, stdin=None):
    proc = subprocess.run([sys.executable, "-I", str(CLI), *args], env=ENV, capture_output=True, text=True, input=stdin)
    if check and proc.returncode != 0:
        raise AssertionError(f"{args}: rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}")
    return proc


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  -- {detail}" if detail and not cond else ""))


def job_output(jid, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        if (tmp / "state" / "jobs" / f"{jid}.exit").exists():
            return (tmp / "state" / "jobs" / f"{jid}.log").read_text()
        time.sleep(0.2)
    raise AssertionError(f"job {jid} did not finish")


def next_request():
    proc = cli("wait", "--timeout", "20")
    lines = [l for l in proc.stdout.splitlines() if l.startswith("r-")]
    assert lines, proc.stdout
    return lines[0].split()[0]


try:
    cli("start")
    check("health", '"session-mediated"' in cli("status").stdout)

    # 1. streaming text answer delivered after keepalives
    jid = cli("job", "start", "--", "stream").stdout.strip()
    rid = next_request()
    prompt = cli("show", rid).stdout
    check("prompt render", "제1화를 써라" in prompt and "system prompt starts" in prompt and "InkOS writer agent" in prompt)
    time.sleep(3.5)  # longer than grace + several keepalives
    answer = tmp / "a.md"
    answer.write_text("비가 내렸다. " * 200)
    cli("reply", rid, "--text-file", str(answer), "--by", "test")
    out = job_output(jid)
    env_line, result = [json.loads(l) for l in out.strip().splitlines()[-2:]]
    check("env base url", env_line["base"] == f"http://127.0.0.1:{PORT}/v1")
    check("proxy stripped", env_line["proxyLeak"] == [], env_line)
    check("stream content intact", result["content"] == answer.read_text(), result.get("content", "")[:50])
    check("stream finish/done/usage", result["finish"] == "stop" and result["done"] and result["usage"], result)
    check("keepalive comments sent", result["comments"] >= 2, result["comments"])
    check("request delivered", json.loads((tmp / "state" / "requests" / rid / "meta.json").read_text())["status"] == "delivered")

    # 1a. wait semantics: EVENT lines, exit 0 for normal outcomes
    idle = cli("wait", "--timeout", "1")
    check("wait timeout is exit 0 with EVENT", idle.returncode == 0 and idle.stdout.startswith("EVENT: timeout"), idle.stdout)
    done = cli("wait", "--job", jid, "--timeout", "5")
    check("wait job-finished is exit 0", done.returncode == 0 and "EVENT: job-finished" in done.stdout and "succeeded" in done.stdout, done.stdout)
    legacy = cli("wait", "--job", jid, "--timeout", "5", "--legacy-codes", check=False)
    check("legacy exit 3 kept on request", legacy.returncode == 3)

    # 1c. protocol tags: shown in prompt, missing tags warn but do not block
    jid = cli("job", "start", "--", "tags").stdout.strip()
    rid = next_request()
    check("tags listed in prompt", "=== CHAPTER_CONTENT ===" in cli("show", rid).stdout)
    warned = cli("reply", rid, "--text", "태그 없는 답")
    check("missing tags warn only", "warning" in warned.stderr and warned.returncode == 0, warned.stderr)
    job_output(jid)

    # 1b. claims: one owner, one answer
    jid = cli("job", "start", "--", "buffered").stdout.strip()
    rid = next_request()
    cli("claim", rid, "--by", "alpha")
    second = cli("claim", rid, "--by", "beta", check=False)
    check("second claim refused", second.returncode != 0, second.stderr)
    stolen = cli("reply", rid, "--text", "beta answer", "--by", "beta", check=False)
    check("reply by non-owner refused", stolen.returncode != 0, stolen.stderr)
    cli("reply", rid, "--text", "alpha answer", "--by", "alpha")
    again = cli("reply", rid, "--text", "again", "--by", "alpha", check=False)
    check("double answer refused", again.returncode != 0, again.stderr)
    result = json.loads(job_output(jid).strip().splitlines()[-1])
    check("owner answer delivered", result.get("message", {}).get("content") == "alpha answer", result)

    # 2. buffered answer, quick (inside grace -> normal 200)
    jid = cli("job", "start", "--", "buffered").stdout.strip()
    rid = next_request()
    cli("reply", rid, "--text", "짧은 답")
    result = json.loads(job_output(jid).strip().splitlines()[-1])
    check("buffered quick", result["status"] == 200 and result["message"]["content"] == "짧은 답", result)

    # 3. buffered answer, slow (whitespace keepalive before JSON)
    jid = cli("job", "start", "--", "buffered").stdout.strip()
    rid = next_request()
    time.sleep(3.5)
    cli("reply", rid, "--text", "늦은 답")
    result = json.loads(job_output(jid).strip().splitlines()[-1])
    check("buffered slow with whitespace keepalive", result.get("message", {}).get("content") == "늦은 답", result)

    # 4. tool call validation + streaming tool call
    jid = cli("job", "start", "--", "tools").stdout.strip()
    rid = next_request()
    bad = cli("reply", rid, "--text", "plain", check=False)
    check("tool_choice=required enforced", bad.returncode != 0 and "requires a tool call" in bad.stderr)
    wrong = cli("reply", rid, "--tool", "nope", "--args-file", "-", stdin="{}", check=False)
    check("unknown tool rejected", wrong.returncode != 0)
    broken = cli("reply", rid, "--tool", "submit_plan", "--args-file", "-", stdin="{goal:", check=False)
    check("invalid JSON args rejected", broken.returncode != 0)
    cli("reply", rid, "--tool", "submit_plan", "--args-file", "-", stdin=json.dumps({"goal": "복수의 시작"}))
    result = json.loads(job_output(jid).strip().splitlines()[-1])
    call = result["toolCalls"][0] if result["toolCalls"] else {}
    check("stream tool call", result["finish"] == "tool_calls" and call.get("function", {}).get("name") == "submit_plan"
          and json.loads(call["function"]["arguments"])["goal"] == "복수의 시작", result)

    # 5. fail inside grace -> HTTP 400
    jid = cli("job", "start", "--", "buffered").stdout.strip()
    rid = next_request()
    cli("fail", rid, "--message", "cannot do this")
    result = json.loads(job_output(jid).strip().splitlines()[-1])
    # 400 when failed inside the header grace window, otherwise an error body after 200.
    check("fail surfaced to inkos", result["status"] in (400, 200) and "cannot do this" in result["body"]
          and "message" not in result, result)

    # 6. fail after headers on a stream -> SSE error event
    jid = cli("job", "start", "--", "stream").stdout.strip()
    rid = next_request()
    time.sleep(2)
    cli("fail", rid, "--message", "late failure", "--retryable")
    result = json.loads(job_output(jid).strip().splitlines()[-1])
    check("late fail -> stream error event", result["error"] and "late failure" in result["error"]["message"] and not result["done"], result)

    # 7. client abort -> request marked abandoned, reply refused
    jid = cli("job", "start", "--", "abort").stdout.strip()
    rid = next_request()
    job_output(jid)
    time.sleep(2.5)
    status = json.loads((tmp / "state" / "requests" / rid / "meta.json").read_text())["status"]
    check("abandoned detected", status == "abandoned", status)
    late = cli("reply", rid, "--text", "too late", check=False)
    check("reply to abandoned refused", late.returncode != 0)

    # 8. claim + studio-config/restore round trip
    cli("studio-config")
    cfg = json.loads((tmp / "project" / "inkos.json").read_text())
    check("studio-config points at bridge", cfg["llm"]["baseUrl"] == f"http://127.0.0.1:{PORT}/v1" and cfg["llm"]["service"] == "custom:Agent")
    check("studio-config keeps no secrets file", not (tmp / "project" / ".inkos" / "secrets.json").exists())
    cli("restore")
    cfg = json.loads((tmp / "project" / "inkos.json").read_text())
    check("restore", cfg["llm"]["baseUrl"] == "https://api.example.com/v1")

    # 9. modelOverrides with a real baseUrl block job start
    cfg["modelOverrides"] = {"writer": {"model": "gpt", "baseUrl": "https://api.openai.com/v1"}}
    (tmp / "project" / "inkos.json").write_text(json.dumps(cfg))
    blocked = cli("job", "start", "--", "stream", check=False)
    check("override bypass blocked", blocked.returncode != 0 and "modelOverrides.writer" in blocked.stderr, blocked.stderr)

    # 10. /v1/responses refused, /v1/models served
    import urllib.request, urllib.error
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=5) as r:
        check("/v1/models", json.load(r)["data"][0]["id"] == "session-assistant")
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/responses", data=b"{}", method="POST"), timeout=5)
        check("/v1/responses refused", False)
    except urllib.error.HTTPError as e:
        check("/v1/responses refused", e.code == 400)
finally:
    cli("stop", check=False)

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
