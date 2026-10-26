#!/usr/bin/env python3
"""InkOS agent bridge: let a coding agent (Claude Code, Codex cloud, Grok, ...)
answer InkOS's LLM calls instead of a paid API.

InkOS believes it talks to an OpenAI-compatible endpoint on 127.0.0.1.  Every
model call is stored as a request file; the agent session reads it, writes the
answer, and `reply` releases the waiting HTTP call.  Standard library only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "1.2.0"
ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("INKOS_AGENT_STATE", ROOT / "runtime")).resolve()
REQUESTS = STATE / "requests"
JOBS = STATE / "jobs"
PORT = int(os.environ.get("INKOS_AGENT_PORT", "4568"))
HOST = "127.0.0.1"
MODEL_ID = os.environ.get("INKOS_AGENT_MODEL", "session-assistant")
BASE_URL = f"http://{HOST}:{PORT}/v1"
# Hold headers back as long as undici allows (headersTimeout 300 s): an answer or
# `fail` inside this window gets a real HTTP status. After it, InkOS's own parser
# treats an error event as an empty response and retries the call (up to 2x).
HEADER_GRACE_S = float(os.environ.get("INKOS_AGENT_HEADER_GRACE_S", "240"))
KEEPALIVE_S = float(os.environ.get("INKOS_AGENT_KEEPALIVE_S", "15"))
MAX_WAIT_S = float(os.environ.get("INKOS_AGENT_MAX_WAIT_S", str(6 * 3600)))
LONG_TIMEOUT_MS = str(int(MAX_WAIT_S * 1000) + 60_000)
OPEN = ("pending", "claimed")
PROXY_KEYS = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
              "ALL_PROXY", "all_proxy", "INKOS_LLM_PROXY_URL")


# ---------------------------------------------------------------- utilities
def now() -> float:
    return time.time()


def stamp(t: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t or now()))


def _retry_sharing(fn, attempts=40):
    # Windows refuses replace/read while another process holds the file open.
    for i in range(attempts):
        try:
            return fn()
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05)


def atomic_write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(3)}.tmp")
    tmp.write_bytes(data.encode() if isinstance(data, str) else data)
    _retry_sharing(lambda: os.replace(tmp, path))


def read_json(path: Path, default=None):
    try:
        return json.loads(_retry_sharing(lambda: path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def create_exclusive(path: Path, content: str = "") -> bool:
    """Atomically create a file; False if it already exists (cross-process safe)."""
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)
    return True


class FileLock:
    """Lock shared by the server and every CLI process (meta.json read-modify-write)."""

    def __init__(self, path: Path, stale_s: float = 10):
        self.path, self.stale_s = path, stale_s

    def __enter__(self):
        deadline = now() + 30
        while not create_exclusive(self.path, str(os.getpid())):
            try:
                if now() - self.path.stat().st_mtime > self.stale_s:
                    self.path.unlink(missing_ok=True)   # holder died mid-update
                    continue
            except FileNotFoundError:
                continue
            if now() > deadline:
                raise TimeoutError(f"lock busy: {self.path}")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)


def write_json(path: Path, value) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


_meta_lock = threading.Lock()


def update_meta(rid: str, only_if: tuple | None = None, **fields) -> dict:
    """Merge fields into meta.json under a cross-process lock.
    only_if: apply only while the current status is one of these."""
    with _meta_lock, FileLock(REQUESTS / rid / ".meta.lock"):
        path = REQUESTS / rid / "meta.json"
        meta = read_json(path, {}) or {}
        if only_if is not None and meta.get("status") not in only_if:
            return meta
        meta.update(fields)
        write_json(path, meta)
        return meta


def new_id(prefix: str) -> str:
    return f"{prefix}{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}"


WINDOWS = os.name == "nt"
# Detached child that survives the agent's shell call (POSIX session / Windows group).
DETACH = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)}
          if WINDOWS else {"start_new_session": True})


def pid_alive(pid: int) -> bool:
    if WINDOWS:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A finished but unreaped child is a zombie, not a running process.
    stat = Path(f"/proc/{pid}/stat")
    return not (stat.exists() and stat.read_text(encoding="utf-8").split(") ")[-1].startswith("Z"))


def pid_image(pid: int) -> str:
    """Executable name of a Windows pid ('' if gone)."""
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout.strip()
    return out.split(",")[0].strip('"').lower() if out.startswith('"') else ""


def kill_tree(pid: int) -> None:
    if WINDOWS:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def die(message: str, code: int = 1):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


# ---------------------------------------------------------------- rendering
def text_of(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for part in content if isinstance(content, list) else [content]:
        if isinstance(part, dict):
            kind = part.get("type")
            if kind in ("text", "input_text"):
                parts.append(part.get("text", ""))
            elif kind in ("image_url", "input_image"):
                url = part.get("image_url", {})
                url = url.get("url", "") if isinstance(url, dict) else str(url)
                parts.append(f"[image attachment omitted: {url[:60]}...]")
            else:
                parts.append(json.dumps(part, ensure_ascii=False))
        else:
            parts.append(str(part))
    return "\n".join(parts)


def system_head(body: dict, limit: int = 100) -> str:
    """Opening of the first system message, so the agent decides the role itself.
    (A keyword guess was removed in 1.2: it misfiled requests too often.)"""
    for m in body.get("messages", []):
        if m.get("role") in ("system", "developer"):
            text = " ".join(text_of(m.get("content")).split())
            return text[:limit] + ("..." if len(text) > limit else "")
    return ""


_TAG_RE = re.compile(r"===\s*([A-Z][A-Z0-9_ ]{1,40}?)\s*===")


def protocol_tags(body: dict) -> list[str]:
    """`=== TAG ===` markers named in the prompt (InkOS parsers rely on them)."""
    text = "\n".join(text_of(m.get("content")) for m in body.get("messages", [])
                     if m.get("role") in ("system", "developer", "user"))
    seen = []
    for tag in _TAG_RE.findall(text):
        tag = " ".join(tag.split())
        if tag not in seen:
            seen.append(tag)
    return seen


def render_prompt(rid: str, endpoint: str, body: dict) -> str:
    lines = [f"# InkOS request {rid}", "",
             f"- endpoint: `{endpoint}`", f"- model requested: `{body.get('model')}`",
             f"- stream: `{bool(body.get('stream'))}`",
             f"- max_tokens: `{body.get('max_tokens') or body.get('max_completion_tokens')}`",
             f"- temperature: `{body.get('temperature')}`",
             f"- system prompt starts: `{system_head(body, 160)}`",
             "- role: decide from the system messages below (the bridge does not guess)"]
    tags = protocol_tags(body)
    if tags:
        lines.append("- output tags named in the prompt: " + ", ".join(f"`=== {t} ===`" for t in tags)
                     + " (keep exactly the ones the required output format uses)")
    if body.get("response_format"):
        lines.append(f"- response_format: `{json.dumps(body['response_format'], ensure_ascii=False)[:2000]}`")
    if body.get("tool_choice") is not None:
        lines.append(f"- tool_choice: `{json.dumps(body['tool_choice'], ensure_ascii=False)}`")
    if endpoint.endswith("images/generations"):
        lines += ["", "## Image request", "", "```json",
                  json.dumps(body, ensure_ascii=False, indent=2), "```", "",
                  f"Answer: `inkos-agent reply {rid} --image file.png` or `inkos-agent fail {rid} --message ...`"]
        return "\n".join(lines) + "\n"
    tools = body.get("tools") or []
    if tools:
        lines += ["", "## Tools you may call", ""]
        for tool in tools:
            fn = tool.get("function", tool)
            lines += [f"### `{fn.get('name')}`", "", fn.get("description", "").strip(), "",
                      "```json", json.dumps(fn.get("parameters", {}), ensure_ascii=False, indent=2), "```", ""]
    lines += ["", "## Messages", ""]
    for i, msg in enumerate(body.get("messages", [])):
        role = msg.get("role")
        header = f"### [{i}] {role}"
        if role == "tool":
            header += f" (tool_call_id={msg.get('tool_call_id')})"
        lines += [header, "", text_of(msg.get("content")), ""]
        for call in msg.get("tool_calls") or []:
            fn = call.get("function", {})
            lines += [f"> assistant called `{fn.get('name')}` id={call.get('id')}", "",
                      "```json", fn.get("arguments", ""), "```", ""]
    lines += ["---", "", "## How to answer", "",
              "Write ONLY what the final assistant message should contain (no commentary about this bridge).",
              f"- text:  `inkos-agent reply {rid} --text-file answer.md`",
              f"- tool:  `inkos-agent reply {rid} --tool NAME --args-file args.json` (repeat --tool/--args-file for several calls)",
              f"- fail:  `inkos-agent fail {rid} --message \"reason\"`"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- server
def build_completion(rid: str, body: dict, answer: dict) -> dict:
    message: dict = {"role": "assistant", "content": answer.get("text") or ""}
    calls = answer.get("tool_calls") or []
    if calls:
        message["tool_calls"] = calls
        if not message["content"]:
            message["content"] = None
    return {"id": f"chatcmpl-{rid}", "object": "chat.completion", "created": int(now()),
            "model": body.get("model") or MODEL_ID,
            "choices": [{"index": 0, "message": message,
                         "finish_reason": "tool_calls" if calls else "stop"}],
            # Real token counts are unknown to the bridge; zeros say "not measured".
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}


def stream_chunks(rid: str, body: dict, answer: dict):
    base = {"id": f"chatcmpl-{rid}", "object": "chat.completion.chunk",
            "created": int(now()), "model": body.get("model") or MODEL_ID}

    def chunk(delta, finish=None):
        return {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}

    yield chunk({"role": "assistant", "content": ""})
    text = answer.get("text") or ""
    for start in range(0, len(text), 400):
        yield chunk({"content": text[start:start + 400]})
    calls = answer.get("tool_calls") or []
    for index, call in enumerate(calls):
        yield chunk({"tool_calls": [{"index": index, "id": call["id"], "type": "function",
                                     "function": {"name": call["function"]["name"],
                                                  "arguments": call["function"]["arguments"]}}]})
    yield chunk({}, "tool_calls" if calls else "stop")
    if (body.get("stream_options") or {}).get("include_usage"):
        yield {**base, "choices": [], "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}


class Handler(BaseHTTPRequestHandler):
    server_version = f"inkos-agent-bridge/{VERSION}"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{stamp()}] {self.address_string()} {fmt % args}\n")

    def send_json(self, status: int, value, close=False):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if close:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/health", "/v1/health"):
            counts: dict[str, int] = {}
            for meta in iter_meta():
                counts[meta.get("status", "?")] = counts.get(meta.get("status", "?"), 0) + 1
            self.send_json(200, {"mode": "session-mediated", "bridge": VERSION, "pid": os.getpid(),
                                 "base_url": BASE_URL, "state": str(STATE), "root": str(ROOT), "requests": counts})
        elif path in ("/v1/models", "/models"):
            self.send_json(200, {"object": "list", "data": [
                {"id": MODEL_ID, "object": "model", "owned_by": "agent-session"}]})
        else:
            self.send_json(404, {"error": {"message": f"unknown path {path}"}})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self.send_json(400, {"error": {"message": "invalid JSON body"}})
        if path.endswith("/chat/completions"):
            kind = "chat"
        elif path.endswith("/images/generations"):
            kind = "image"
        elif path.endswith("/responses"):
            return self.send_json(400, {"error": {"type": "invalid_request_error", "message":
                "The agent bridge implements Chat Completions only. Set apiFormat to 'chat' "
                "(INKOS_LLM_API_FORMAT=chat)."}})
        else:
            return self.send_json(404, {"error": {"message": f"unknown path {path}"}})
        while True:
            rid = new_id("r-")
            folder = REQUESTS / rid
            try:
                folder.mkdir(parents=True)
                break
            except FileExistsError:
                continue
        write_json(folder / "request.json", body)
        atomic_write(folder / "prompt.md", render_prompt(rid, path, body))
        update_meta(rid, id=rid, kind=kind, endpoint=path, status="pending", created=now(),
                    created_at=stamp(), stream=bool(body.get("stream")) and kind == "chat",
                    system_head=system_head(body) if kind == "chat" else "image request",
                    protocol_tags=protocol_tags(body) if kind == "chat" else [],
                    tools=[(t.get("function") or t).get("name") for t in body.get("tools") or []],
                    max_tokens=body.get("max_tokens") or body.get("max_completion_tokens"))
        self.log_message("queued %s %s", rid, path)
        try:
            if kind == "chat" and body.get("stream"):
                self.serve_stream(rid, body)
            else:
                self.serve_buffered(rid, body, kind)
        except OSError:
            update_meta(rid, only_if=OPEN, status="abandoned", abandoned_at=stamp())
            self.log_message("client went away for %s", rid)

    # Wait for response.json; call tick() while waiting (keepalive / abandonment).
    def wait_answer(self, rid: str, deadline: float, tick=None):
        folder = REQUESTS / rid
        last = now()
        while now() < deadline:
            answer = read_json(folder / "response.json")
            if answer is not None:
                return answer
            meta = read_json(folder / "meta.json", {})
            if meta.get("status") == "cancelled":
                return {"error": {"message": "cancelled by agent", "retryable": False}}
            if tick and now() - last >= KEEPALIVE_S:
                tick()
                last = now()
            time.sleep(0.25)
        return None

    def serve_buffered(self, rid, body, kind):
        started = now()
        answer = self.wait_answer(rid, started + HEADER_GRACE_S)
        if answer is not None and answer.get("error"):
            return self.finish_error(rid, answer["error"], headers_sent=False)
        if answer is None:
            # Send headers now; leading whitespace is valid before a JSON document
            # and keeps the client's body-idle timer alive while the agent works.
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Connection", "close")
            self.end_headers()
            update_meta(rid, headers_sent=True)

            def tick():
                self.wfile.write(b" ")
                self.wfile.flush()
            answer = self.wait_answer(rid, started + MAX_WAIT_S, tick)
            if answer is None or answer.get("error"):
                err = (answer or {}).get("error") or {"message": "agent did not answer in time"}
                self.wfile.write(json.dumps({"error": err}).encode())
                return update_meta(rid, status="failed" if answer else "expired", finished_at=stamp())
            self.wfile.write(json.dumps(self.payload(rid, body, kind, answer), ensure_ascii=False).encode())
        else:
            self.send_json(200, self.payload(rid, body, kind, answer))
        update_meta(rid, status="delivered", finished_at=stamp())

    def payload(self, rid, body, kind, answer):
        if kind == "image":
            return {"created": int(now()), "data": [{"b64_json": answer["image_b64"]}]}
        return build_completion(rid, body, answer)

    def serve_stream(self, rid, body):
        started = now()
        answer = self.wait_answer(rid, started + HEADER_GRACE_S)
        if answer is not None and answer.get("error"):
            return self.finish_error(rid, answer["error"], headers_sent=False)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        update_meta(rid, headers_sent=True)

        def tick():
            # SSE comment: ignored by parsers, but resets HTTP body-idle timers.
            self.wfile.write(b": agent working\n\n")
            self.wfile.flush()
        if answer is None:
            tick()
            answer = self.wait_answer(rid, started + MAX_WAIT_S, tick)
        if answer is None or answer.get("error"):
            err = (answer or {}).get("error") or {"message": "agent did not answer in time"}
            self.wfile.write(f"data: {json.dumps({'error': err}, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()
            return update_meta(rid, status="failed" if answer else "expired", finished_at=stamp())
        for chunk in stream_chunks(rid, body, answer):
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        update_meta(rid, status="delivered", finished_at=stamp())

    def finish_error(self, rid, err, headers_sent):
        status = 503 if err.get("retryable") else 400
        self.send_json(status, {"error": {"type": "agent_session_error", "message": err.get("message", "")}})
        update_meta(rid, status="failed", finished_at=stamp())


def serve(port: int):
    REQUESTS.mkdir(parents=True, exist_ok=True)
    # Bind first: a second bridge must fail here, before touching live requests.
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    # Requests left open by a previous bridge can never be delivered.
    for meta in iter_meta():
        update_meta(meta["id"], only_if=OPEN, status="abandoned", abandoned_at=stamp(), reason="bridge restarted")
    httpd.daemon_threads = True
    print(f"inkos-agent bridge {VERSION} listening on http://{HOST}:{port}/v1 (state: {STATE})", flush=True)
    httpd.serve_forever()


# ---------------------------------------------------------------- client side
def iter_meta():
    if not REQUESTS.exists():
        return []
    out = []
    for folder in sorted(REQUESTS.iterdir()):
        meta = read_json(folder / "meta.json")
        if meta:
            out.append(meta)
    return out


def get_health(timeout=2):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://{HOST}:{PORT}/health", timeout=timeout) as response:
        return json.load(response)


def bridge_up() -> bool:
    try:
        return get_health().get("mode") == "session-mediated"
    except (urllib.error.URLError, OSError, ValueError):
        return False


def foreign_bridge() -> str | None:
    """Why the bridge answering on PORT belongs to another installation (its requests
    would land in that installation's runtime), or None when it is this one or none is up."""
    try:
        health = get_health()
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if health.get("mode") == "session-mediated" and health.get("state") == str(STATE):
        return None
    owner = health.get("state") or f"unknown (bridge {health.get('bridge', '?')} does not report its runtime)"
    return (f"port {PORT} is served by another bridge (pid {health.get('pid', '?')}, runtime {owner}); "
            f"this installation's runtime is {STATE}. Stop that bridge (its own `inkos-agent stop`) "
            f"or set INKOS_AGENT_PORT to a free port")


def inkos_bin() -> str:
    return os.environ.get("INKOS_BIN") or shutil.which("inkos") or "inkos"


def inkos_cmd() -> list[str]:
    """argv prefix for inkos. A .js entry runs under node; on Windows the npm .cmd shim
    is bypassed (it opens a console and mangles arguments containing & or ")."""
    binary = inkos_bin()
    if binary.lower().endswith((".js", ".mjs")):
        return [shutil.which("node") or "node", binary]
    if WINDOWS and binary.lower().endswith((".cmd", ".bat")):
        entry = Path(binary).parent / "node_modules" / "@actalk" / "inkos" / "dist" / "index.js"
        if entry.exists():
            return [shutil.which("node") or "node", str(entry)]
    return [binary]


def project_dir(args) -> Path:
    value = getattr(args, "project", None) or os.environ.get("INKOS_AGENT_PROJECT") or os.getcwd()
    return Path(value).expanduser().resolve()


def inkos_env(keep_proxy=False) -> dict:
    env = dict(os.environ)
    if not keep_proxy:
        # Stock InkOS (without the Korean patch's loopback bypass) sends even
        # 127.0.0.1 through HTTPS_PROXY in cloud sandboxes. Side effect: outbound
        # features (web search, remote covers) lose the proxy; use --keep-proxy.
        for key in PROXY_KEYS:
            env.pop(key, None)
    env.update({
        "INKOS_LLM_SERVICE": "custom", "INKOS_LLM_PROVIDER": "openai",
        "INKOS_LLM_BASE_URL": BASE_URL, "INKOS_LLM_MODEL": MODEL_ID,
        # Loopback needs no key; a fixed marker keeps a real key from .env out of requests.
        "INKOS_LLM_API_KEY": "agent-session-local",
        "INKOS_LLM_API_FORMAT": "chat", "INKOS_LLM_STREAM": env.get("INKOS_LLM_STREAM", "true"),
        "INKOS_LLM_FIRST_EVENT_TIMEOUT_MS": LONG_TIMEOUT_MS,
        "INKOS_LLM_STREAM_IDLE_TIMEOUT_MS": LONG_TIMEOUT_MS,
        "INKOS_LLM_REQUEST_TIMEOUT_MS": LONG_TIMEOUT_MS,
    })
    return env


def override_problems(project: Path) -> list[str]:
    config = read_json(project / "inkos.json", {}) or {}
    problems = []
    for name, value in (config.get("modelOverrides") or {}).items():
        if isinstance(value, dict) and value.get("baseUrl") \
                and value["baseUrl"].rstrip("/") != BASE_URL:
            problems.append(f"modelOverrides.{name} -> {value['baseUrl']} (bypasses the bridge: real API call)")
    return problems


def cmd_start(args):
    STATE.mkdir(parents=True, exist_ok=True)
    foreign = foreign_bridge()
    if foreign:
        die(foreign, 3)
    if not bridge_up():
        log = (STATE / "bridge.log").open("a")
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "serve"],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 cwd=str(ROOT), **DETACH)
        atomic_write(STATE / "bridge.pid", str(child.pid))
        for _ in range(50):
            if bridge_up():
                break
            time.sleep(0.1)
        else:
            die(f"bridge did not start; see {STATE / 'bridge.log'}")
    print(f"bridge ready: {BASE_URL}")
    if args.studio:
        project = project_dir(args)
        if not (project / "inkos.json").exists():
            die(f"no inkos.json in {project}")
        cfg = (read_json(project / "inkos.json", {}) or {}).get("llm", {})
        if cfg.get("baseUrl") != BASE_URL:
            die("Studio ignores INKOS_LLM_* env. Run `inkos-agent studio-config` first (restore later with `inkos-agent restore`).")
        log = (STATE / "studio.log").open("a")
        child = subprocess.Popen([*inkos_cmd(), "studio"], cwd=project, env=inkos_env(args.keep_proxy),
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, **DETACH)
        atomic_write(STATE / "studio.pid", str(child.pid))
        print(f"studio starting in {project} (log: {STATE / 'studio.log'})")


def stop_pid(name: str, expect: bytes):
    path = STATE / f"{name}.pid"
    if not path.exists():
        return
    pid = int(path.read_text(encoding="utf-8"))
    cmdline = Path(f"/proc/{pid}/cmdline")
    if cmdline.exists() and expect not in cmdline.read_bytes():
        die(f"pid {pid} is not {name}; refusing to kill")
    if WINDOWS:
        image = pid_image(pid)
        if image and not image.startswith(("python", "py.exe", "node", "cmd")):
            die(f"pid {pid} is now {image} (stale pid file); refusing to kill")
    if pid_alive(pid):
        kill_tree(pid)
    path.unlink()
    print(f"stopped {name}")


def cmd_stop(args):
    stop_pid("studio", b"inkos")
    stop_pid("bridge", b"inkos_agent.py")


def cmd_status(args):
    print(json.dumps(get_health() if bridge_up() else {"bridge": "down", "expected": BASE_URL}, indent=2))
    for job in list_jobs():
        print(f"job {job['id']}: {job['state']}  inkos {' '.join(job['args'])}")


def cmd_doctor(args):
    ok = True
    project = project_dir(args)
    binary = shutil.which(inkos_bin()) or inkos_bin()
    try:
        version = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        version = None
    print(f"inkos binary : {binary} ({version or 'NOT RUNNABLE'})")
    ok &= bool(version)
    node = shutil.which("node")
    print(f"node         : {subprocess.run(['node', '--version'], capture_output=True, text=True).stdout.strip() if node else 'missing'}")
    print(f"project      : {project} ({'ok' if (project / 'inkos.json').exists() else 'no inkos.json'})")
    foreign = foreign_bridge()
    if foreign:
        ok = False
        print(f"bridge       : up at {BASE_URL}, but NOT this installation's")
        print(f"WARNING      : {foreign}")
    else:
        print(f"bridge       : {'up' if bridge_up() else 'down'} at {BASE_URL}")
    proxies = [k for k in PROXY_KEYS if os.environ.get(k)]
    print(f"proxy env    : {', '.join(proxies) or 'none'} ({'stripped for inkos jobs' if proxies else 'nothing to strip'})")
    for problem in override_problems(project):
        ok = False
        print(f"WARNING      : {problem}")
    config = read_json(project / "inkos.json", {}) or {}
    if (config.get("llm") or {}).get("apiFormat") == "responses":
        print("note         : project apiFormat=responses; jobs force chat via INKOS_LLM_API_FORMAT")
    raise SystemExit(0 if ok else 1)


# ---------------------------------------------------------------- jobs
def list_jobs():
    out = []
    if not JOBS.exists():
        return out
    for path in sorted(JOBS.glob("*.json")):
        job = read_json(path)
        if not job:
            continue
        exit_file = JOBS / f"{job['id']}.exit"
        if exit_file.exists():
            job["state"], job["exit_code"] = "finished", int(exit_file.read_text(encoding="utf-8").strip() or 1)
        elif pid_alive(job["pid"]):
            job["state"] = "running"
        else:
            job["state"] = "lost"
        out.append(job)
    return out


def get_job(jid: str) -> dict:
    for job in list_jobs():
        if job["id"] == jid:
            return job
    die(f"no job {jid}")


def strip_dashes(rest):
    return rest[1:] if rest[:1] == ["--"] else rest


def cmd_run(args):
    project = project_dir(args)
    rest = strip_dashes(args.rest)
    if not rest:
        die("usage: inkos-agent run -- <inkos args>")
    raise SystemExit(subprocess.call([*inkos_cmd(), *rest], cwd=project, env=inkos_env(args.keep_proxy)))


def cmd_job(args):
    if args.job_cmd == "start":
        rest = strip_dashes(args.rest)
        if not rest:
            die("usage: inkos-agent job start -- <inkos args>")
        foreign = foreign_bridge()
        if foreign:
            die(foreign, 3)
        if not bridge_up():
            die("bridge is down; run `inkos-agent start` first")
        project = project_dir(args)
        problems = override_problems(project)
        if problems and not args.allow_overrides:
            die("refusing to start: " + "; ".join(problems) + " (pass --allow-overrides to accept)")
        JOBS.mkdir(parents=True, exist_ok=True)
        jid = new_id("j-")
        log = (JOBS / f"{jid}.log").open("a")
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_jobrun", jid, str(project),
                                  "1" if args.keep_proxy else "0", *rest],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, **DETACH)
        write_json(JOBS / f"{jid}.json", {"id": jid, "pid": child.pid, "args": rest,
                                          "project": str(project), "started_at": stamp()})
        print(jid)
    elif args.job_cmd == "list":
        for job in list_jobs():
            extra = f" exit={job['exit_code']}" if "exit_code" in job else ""
            print(f"{job['id']}  {job['state']}{extra}  {job['started_at']}  inkos {' '.join(job['args'])}")
    elif args.job_cmd == "status":
        print(json.dumps(get_job(args.id), ensure_ascii=False, indent=2))
    elif args.job_cmd == "log":
        get_job(args.id)
        lines = (JOBS / f"{args.id}.log").read_text(encoding="utf-8", errors="replace").splitlines()
        print("\n".join(lines[-args.tail:] if args.tail else lines))
    elif args.job_cmd == "stop":
        job = get_job(args.id)
        if job["state"] == "running":
            kill_tree(job["pid"])
            print(f"sent SIGTERM to {args.id}")
        # InkOS closes its sockets on exit; the server then marks those requests abandoned.


def cmd_jobrun(argv):
    jid, project, keep_proxy, *rest = argv
    try:
        code = subprocess.call([*inkos_cmd(), *rest], cwd=project, env=inkos_env(keep_proxy == "1"))
    except OSError as error:
        print(f"cannot run inkos: {error}", flush=True)
        code = 127
    atomic_write(JOBS / f"{jid}.exit", str(code))


# ---------------------------------------------------------------- queue commands
def open_requests():
    return [m for m in iter_meta() if m.get("status") in OPEN]


def summary(meta: dict) -> str:
    prompt = REQUESTS / meta["id"] / "prompt.md"
    size = prompt.stat().st_size if prompt.exists() else 0
    tools = f" tools={','.join(meta['tools'])}" if meta.get("tools") else ""
    claimed = f" claimed_by={meta.get('claimed_by')}" if meta.get("status") == "claimed" else ""
    return (f"{meta['id']}  {meta['status']}  {meta.get('kind')}"
            f"  max_tokens={meta.get('max_tokens')}{tools}{claimed}  prompt={prompt} ({size} bytes)"
            f"\n    system: {meta.get('system_head') or meta.get('role_guess', '')}")


def cmd_pending(args):
    items = open_requests()
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        for meta in items:
            print(summary(meta))
        if not items:
            print("(no open requests)")


def cmd_wait(args):
    deadline = now() + args.timeout
    while True:
        items = [m for m in open_requests() if args.include_claimed or m["status"] == "pending"]
        if items:
            print(f"EVENT: request ({len(items)} open)")
            for meta in items:
                print(summary(meta))
            raise SystemExit(0)
        if args.job:
            job = get_job(args.job)
            if job["state"] != "running":
                code = job.get("exit_code")
                verdict = "succeeded" if code == 0 else "FAILED"
                print(f"EVENT: job-finished {job['id']} {verdict} (inkos exit={code}, state={job['state']})")
                print("\n".join((JOBS / f"{job['id']}.log").read_text(encoding="utf-8", errors="replace").splitlines()[-25:]))
                raise SystemExit(3 if args.legacy_codes else 0)
        if now() >= deadline:
            print("EVENT: timeout (nothing pending yet; call wait again)")
            raise SystemExit(4 if args.legacy_codes else 0)
        time.sleep(1)


def require_meta(rid: str) -> dict:
    meta = read_json(REQUESTS / rid / "meta.json")
    if not meta:
        die(f"no request {rid}")
    return meta


def cmd_show(args):
    meta = require_meta(args.id)
    folder = REQUESTS / args.id
    if args.path:
        print(folder / ("request.json" if args.raw else "prompt.md"))
    elif args.raw:
        print((folder / "request.json").read_text(encoding="utf-8"))
    else:
        print((folder / "prompt.md").read_text(encoding="utf-8"))
    if meta.get("status") not in OPEN:
        print(f"\n[note] request status is {meta.get('status')}; it no longer accepts an answer.", file=sys.stderr)


def cmd_claim(args):
    meta = require_meta(args.id)
    if meta.get("status") != "pending" and not args.force:
        die(f"{args.id} is {meta.get('status')} (claimed_by={meta.get('claimed_by')})")
    lock = REQUESTS / args.id / ".claim.lock"
    if not create_exclusive(lock, args.by):
        if not args.force:
            die(f"{args.id} was just claimed by {lock.read_text(encoding='utf-8')}")
        atomic_write(lock, args.by)
    meta = update_meta(args.id, only_if=OPEN, status="claimed", claimed_by=args.by, claimed_at=stamp())
    if meta.get("claimed_by") != args.by:
        die(f"{args.id} is {meta.get('status')}; claim not applied")
    print(f"claimed {args.id} for {args.by}")


def read_text_arg(value: str | None) -> str | None:
    if value is None:
        return None
    return sys.stdin.buffer.read().decode("utf-8") if value == "-" else Path(value).read_text(encoding="utf-8")


def schema_required(body: dict) -> list[str]:
    fmt = body.get("response_format") or {}
    schema = (fmt.get("json_schema") or {}).get("schema") or {}
    return list(schema.get("required") or [])


def check_answerable(args) -> dict:
    meta = require_meta(args.id)
    if meta.get("status") not in OPEN:
        die(f"{args.id} is {meta.get('status')}; InkOS is no longer waiting for it")
    if meta.get("status") == "claimed" and meta.get("claimed_by") != args.by and not args.force:
        die(f"{args.id} is claimed by {meta.get('claimed_by')}; answer with --by {meta.get('claimed_by')} or --force")
    return meta


def commit_answer(args, payload: dict, status: str):
    # Exactly one answer per request, even with several agents racing.
    if not create_exclusive(REQUESTS / args.id / ".answer.lock", args.by):
        die(f"{args.id} already has an answer")
    write_json(REQUESTS / args.id / "response.json", payload)
    update_meta(args.id, only_if=OPEN, status=status, answered_by=args.by, answered_at=stamp())


def cmd_reply(args):
    meta = check_answerable(args)
    body = read_json(REQUESTS / args.id / "request.json", {})
    if meta.get("kind") == "image":
        if not args.image:
            die("image request: use --image file.png")
        answer = {"image_b64": base64.b64encode(Path(args.image).read_bytes()).decode()}
    else:
        text = read_text_arg(args.text_file)
        if text is None and args.text is not None:
            text = args.text
        names = args.tool or []
        arg_files = args.args_file or []
        if len(names) != len(arg_files):
            die("each --tool needs a matching --args-file")
        offered = {(t.get("function") or t).get("name") for t in body.get("tools") or []}
        calls = []
        for name, file in zip(names, arg_files):
            if name not in offered:
                die(f"tool {name!r} was not offered (offered: {sorted(offered) or 'none'})")
            raw = read_text_arg(file)
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as error:
                die(f"{file}: arguments are not valid JSON ({error})")
            if not isinstance(parsed, dict):
                die(f"{file}: tool arguments must be a JSON object")
            calls.append({"id": f"call_{secrets.token_hex(8)}", "type": "function",
                          "function": {"name": name, "arguments": json.dumps(parsed, ensure_ascii=False)}})
        choice = body.get("tool_choice")
        if not calls and (choice == "required" or isinstance(choice, dict)) and not args.force:
            die(f"this request requires a tool call (tool_choice={json.dumps(choice)})")
        if not calls and not (text or "").strip() and not args.force:
            die("empty answer; give --text-file/--text or --tool")
        fmt = (body.get("response_format") or {}).get("type")
        if fmt in ("json_object", "json_schema") and not calls and not args.force:
            try:
                doc = json.loads(text)
            except json.JSONDecodeError as error:
                die(f"response_format={fmt} but the answer is not JSON ({error}); fix it or pass --force")
            missing = [k for k in schema_required(body) if not isinstance(doc, dict) or k not in doc]
            if missing:
                die(f"JSON answer misses required keys {missing}; fix it or pass --force")
        tags = meta.get("protocol_tags") or []
        if tags and not calls and text and not any(f"=== {t} ===" in " ".join(text.split()) or f"==={t}===" in text
                                                    for t in tags):
            print("warning: the prompt names output tags (" + ", ".join(f"=== {t} ===" for t in tags[:6])
                  + ") but the answer contains none; InkOS may fail to parse it. "
                  "Check the required output format (warning only).", file=sys.stderr)
        answer = {"text": text or "", "tool_calls": calls}
    answer.update(answered_by=args.by, answered_at=stamp())
    commit_answer(args, answer, "answered")
    print(f"answered {args.id}" + (f" with {len(answer.get('tool_calls') or [])} tool call(s)" if answer.get("tool_calls") else ""))


def cmd_fail(args):
    meta = check_answerable(args)
    if meta.get("headers_sent"):
        print("note: headers already sent; InkOS will see an empty response and may retry this call "
              "as a new request", file=sys.stderr)
    commit_answer(args, {"error": {"message": args.message, "retryable": args.retryable},
                         "answered_by": args.by}, "failing")
    print(f"failed {args.id}: {args.message}")


def cmd_gc(args):
    cutoff = now() - args.older_than_hours * 3600
    removed = 0
    for meta in iter_meta():
        if meta.get("status") not in OPEN and meta.get("created", now()) < cutoff:
            shutil.rmtree(REQUESTS / meta["id"], ignore_errors=True)
            removed += 1
    print(f"removed {removed} finished request folder(s)")


# ---------------------------------------------------------------- studio config
def cmd_studio_config(args):
    project = project_dir(args)
    path = project / "inkos.json"
    if not path.exists():
        die(f"no inkos.json in {project}")
    backup = project / "inkos.pre-agent.json"
    original = path.read_text(encoding="utf-8")
    if backup.exists() and not args.rebackup:
        print(f"keeping existing backup {backup.name}")
    else:
        atomic_write(backup, original)
    config = json.loads(original)
    llm = config.setdefault("llm", {})
    services = [s for s in llm.get("services", [])
                if not (s.get("service") == "custom" and s.get("name") in ("Session", "Autonomous", "Agent"))]
    services.append({"service": "custom", "name": "Agent", "baseUrl": BASE_URL,
                     "models": [MODEL_ID], "apiFormat": "chat", "stream": True})
    llm.update(provider="openai", service="custom:Agent", configSource="studio", baseUrl=BASE_URL,
               model=MODEL_ID, defaultModel=MODEL_ID, apiFormat="chat", stream=True, services=services)
    write_json(path, config)
    ignore = project / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    if "inkos.pre-agent.json" not in text.splitlines():
        atomic_write(ignore, text + ("" if not text or text.endswith("\n") else "\n") + "inkos.pre-agent.json\n")
    print(f"{path.name} now points Studio at {BASE_URL}; original saved as {backup.name}")
    print("Not changed: writing/revision gates, cover/image settings, modelOverrides.")
    for problem in override_problems(project):
        print(f"WARNING: {problem}")


def cmd_restore(args):
    project = project_dir(args)
    backup = project / "inkos.pre-agent.json"
    legacy = project / "inkos.pre-session.json"
    source = backup if backup.exists() else legacy if legacy.exists() else None
    if not source:
        die("no backup found (inkos.pre-agent.json / inkos.pre-session.json)")
    atomic_write(project / "inkos.json", source.read_text(encoding="utf-8"))
    print(f"restored inkos.json from {source.name}")


def cmd_api(args):
    if not args.path.startswith("/api/v1/"):
        die("only local Studio /api/v1/ routes are accepted")
    port = os.environ.get("INKOS_STUDIO_PORT", "4567")
    data = Path(args.body_file).read_bytes() if args.body_file else None
    request = urllib.request.Request(f"http://127.0.0.1:{port}{args.path}", data=data, method=args.method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=MAX_WAIT_S) as response:
        payload = response.read()
    if args.output:
        Path(args.output).write_bytes(payload)
    else:
        print(payload.decode())


def cmd_env(args):
    env = inkos_env(args.keep_proxy)
    for key in sorted(k for k in env if k.startswith("INKOS_LLM_")):
        print(f"export {key}={json.dumps(env[key])}")
    if not args.keep_proxy:
        print("unset " + " ".join(PROXY_KEYS))


# ---------------------------------------------------------------- argparse
def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["_jobrun"]:
        return cmd_jobrun(argv[1:])
    parser = argparse.ArgumentParser(prog="inkos-agent", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def with_project(p):
        p.add_argument("--project", help="InkOS project dir (default: $INKOS_AGENT_PROJECT or cwd)")
        p.add_argument("--keep-proxy", action="store_true", help="do not strip HTTP(S)_PROXY for inkos")
        return p

    sub.add_parser("serve", help="run the bridge in the foreground").set_defaults(fn=lambda a: serve(PORT))
    p = with_project(sub.add_parser("start", help="start the bridge in the background"))
    p.add_argument("--studio", action="store_true", help="also start `inkos studio` (needs studio-config)")
    p.set_defaults(fn=cmd_start)
    sub.add_parser("stop", help="stop bridge and studio").set_defaults(fn=cmd_stop)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    with_project(sub.add_parser("doctor", help="check inkos, project, proxy, overrides")).set_defaults(fn=cmd_doctor)
    with_project(sub.add_parser("env", help="print shell exports for manual inkos use")).set_defaults(fn=cmd_env)
    p = with_project(sub.add_parser("run", help="run a short inkos command in the foreground"))
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_run)

    job = sub.add_parser("job", help="long inkos commands in the background")
    jsub = job.add_subparsers(dest="job_cmd", required=True)
    p = with_project(jsub.add_parser("start"))
    p.add_argument("--allow-overrides", action="store_true")
    p.add_argument("rest", nargs=argparse.REMAINDER)
    jsub.add_parser("list")
    for name in ("status", "stop"):
        jsub.add_parser(name).add_argument("id")
    p = jsub.add_parser("log")
    p.add_argument("id")
    p.add_argument("--tail", type=int, default=60)
    job.set_defaults(fn=cmd_job)

    p = sub.add_parser("pending", help="list open requests")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_pending)
    p = sub.add_parser("wait", help="block until a request is pending, the job ends, or timeout; "
                                    "first line 'EVENT: request|job-finished|timeout' (exit 0)")
    p.add_argument("--timeout", type=float, default=90)
    p.add_argument("--job")
    p.add_argument("--include-claimed", action="store_true")
    p.add_argument("--legacy-codes", action="store_true",
                   help="exit 3 on job end and 4 on timeout (pre-1.2 behaviour)")
    p.set_defaults(fn=cmd_wait)
    p = sub.add_parser("show", help="print a request as readable markdown")
    p.add_argument("id")
    p.add_argument("--raw", action="store_true", help="original JSON body")
    p.add_argument("--path", action="store_true", help="print the file path only")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("claim", help="mark a request as taken by a (sub)agent")
    p.add_argument("id")
    p.add_argument("--by", default="main")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_claim)
    p = sub.add_parser("reply", help="answer a request")
    p.add_argument("id")
    p.add_argument("--text-file", help="file with the assistant text ('-' = stdin)")
    p.add_argument("--text", help="inline text (short answers only)")
    p.add_argument("--tool", action="append", help="tool name to call (repeatable)")
    p.add_argument("--args-file", action="append", help="JSON arguments file for the matching --tool")
    p.add_argument("--image", help="PNG/JPEG file for an image request")
    p.add_argument("--by", default=os.environ.get("INKOS_AGENT_NAME", "agent"))
    p.add_argument("--force", action="store_true", help="skip format checks")
    p.set_defaults(fn=cmd_reply)
    p = sub.add_parser("fail", help="return an error to InkOS for this request")
    p.add_argument("id")
    p.add_argument("--message", required=True)
    p.add_argument("--retryable", action="store_true", help="HTTP 503 so InkOS may retry")
    p.add_argument("--force", action="store_true", help="ignore another agent's claim")
    p.add_argument("--by", default=os.environ.get("INKOS_AGENT_NAME", "agent"))
    p.set_defaults(fn=cmd_fail)
    p = sub.add_parser("gc", help="delete finished request folders")
    p.add_argument("--older-than-hours", type=float, default=24)
    p.set_defaults(fn=cmd_gc)
    p = with_project(sub.add_parser("studio-config", help="point inkos.json (Studio) at the bridge, with backup"))
    p.add_argument("--rebackup", action="store_true", help="overwrite an existing backup")
    p.set_defaults(fn=cmd_studio_config)
    with_project(sub.add_parser("restore", help="restore inkos.json from the backup")).set_defaults(fn=cmd_restore)
    p = sub.add_parser("api", help="call the local Studio REST API")
    p.add_argument("method", choices=["GET", "POST", "PUT", "DELETE"])
    p.add_argument("path")
    p.add_argument("--body-file")
    p.add_argument("--output")
    p.set_defaults(fn=cmd_api)

    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
