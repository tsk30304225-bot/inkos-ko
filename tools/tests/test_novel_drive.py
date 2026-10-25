#!/usr/bin/env python3
"""Offline test of tools/novel-drive.py against a fake Drive API (no network, no real credentials)."""
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TOOL = Path(__file__).resolve().parent.parent / "novel-drive.py"
FILES: dict[str, dict] = {}
UPLOADS: dict[str, dict] = {}
results = []


class FakeDrive(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body=b"", headers=None):
        self.send_response(code)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if self.headers.get("Authorization") != "Bearer fake-access":
            self.reply(401, b'{"error":"auth"}')
            return False
        return True

    def body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", "0")))

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/token":
            form = parse_qs(self.body().decode())
            ok = form.get("refresh_token") == ["fake-refresh"] and form.get("grant_type") == ["refresh_token"]
            return self.reply(200 if ok else 400, json.dumps({"access_token": "fake-access"} if ok else {"error": "bad"}).encode())
        if url.path == "/api/files" and self.authorized():
            meta = json.loads(self.body())
            return self.reply(200, json.dumps({"id": "folder1", "name": meta["name"]}).encode())
        if url.path == "/upload" and self.authorized():
            meta = json.loads(self.body())
            upload_id = f"u{len(UPLOADS)}"
            UPLOADS[upload_id] = meta
            port = self.server.server_address[1]
            return self.reply(200, b"", {"Location": f"http://127.0.0.1:{port}/session/{upload_id}"})

    def do_PUT(self):
        url = urlparse(self.path)
        if url.path.startswith("/session/") and self.authorized():
            meta = UPLOADS[url.path.rsplit("/", 1)[1]]
            file_id = f"f{len(FILES)}"
            FILES[file_id] = {**meta, "id": file_id, "data": self.body(), "createdTime": f"2026-10-25T00:00:{len(FILES):02d}Z", "trashed": False}
            return self.reply(200, json.dumps({"id": file_id, "name": meta["name"]}).encode())

    def do_GET(self):
        url = urlparse(self.path)
        if not self.authorized():
            return
        if url.path == "/api/files":
            query = parse_qs(url.query)["q"][0]
            items = [f for f in FILES.values() if not f["trashed"] and f["parents"][0] in query]
            items.sort(key=lambda f: f["createdTime"], reverse=True)
            return self.reply(200, json.dumps({"files": [{"id": f["id"], "name": f["name"], "size": str(len(f["data"])), "createdTime": f["createdTime"]} for f in items]}).encode())
        if url.path.startswith("/api/files/") and parse_qs(url.query).get("alt") == ["media"]:
            return self.reply(200, FILES[url.path.rsplit("/", 1)[1]]["data"])
        self.reply(404)

    def do_PATCH(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/files/") and self.authorized():
            FILES[url.path.rsplit("/", 1)[1]].update(json.loads(self.body()))
            return self.reply(200, b"{}")


def check(name, condition, detail=""):
    results.append(bool(condition))
    print(("PASS " if condition else "FAIL ") + name + (f" — {detail}" if detail and not condition else ""))


server = ThreadingHTTPServer(("127.0.0.1", 0), FakeDrive)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
tmp = Path(tempfile.mkdtemp(prefix="novel-drive-test-"))
env = {k: v for k, v in os.environ.items() if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
env.update({"INKOS_GDRIVE_TEST_TOKEN_URL": f"{base}/token", "INKOS_GDRIVE_TEST_API": f"{base}/api", "INKOS_GDRIVE_TEST_UPLOAD": f"{base}/upload"})


def run(*args, extra=None):
    return subprocess.run([sys.executable, "-I", str(TOOL), *args], env={**env, **(extra or {})}, capture_output=True, text=True)


project = tmp / "내-소설"
(project / "works" / "달빛" / "source" / "chapters").mkdir(parents=True)
(project / "inkos.json").write_text('{"language":"ko"}', encoding="utf-8")
(project / "works" / "달빛" / "source" / "chapters" / "0001_시작.md").write_text("# 제1화 시작\n\n본문", encoding="utf-8")
(project / ".env").write_text("SECRET=1")
(project / "runtime").mkdir()
(project / "runtime" / "cache.json").write_text("{}")

out = tmp / "a.tar.gz"
r = run("pack", str(project), "-o", str(out))
check("pack ok", r.returncode == 0, r.stderr)
names = tarfile.open(out).getnames()
check("pack keeps manuscripts", "works/달빛/source/chapters/0001_시작.md" in names, str(names))
check("pack skips .env and runtime/", ".env" not in names and not any(n.startswith("runtime/") for n in names), str(names))
named = tmp / "내-소설_20261025-2330_2화.tar.gz"
r = run("pack", str(project), str(named))
check("pack accepts the archive name as a second argument", r.returncode == 0 and named.exists(), r.stdout + r.stderr)
r = run("unpack", str(out), str(tmp / "restored"))
check("unpack ok", r.returncode == 0 and (tmp / "restored/works/달빛/source/chapters/0001_시작.md").read_text(encoding="utf-8").endswith("본문"), r.stderr)
r = run("unpack", str(out), str(tmp / "restored"))
check("unpack refuses to overwrite a project without --force", r.returncode != 0)

import hashlib
resume_project = tmp / "이어쓰기"
work = resume_project / "works" / "달빛"
for rel, text in {
    "source/book.json": '{"language":"ko"}',
    "source/chapters/0001_시작.md": "# 제1화 시작\n\n본문",
    "source/story/state/manifest.json": '{"lastAppliedChapter":3}',
    "source/story/memory.db": "index",
    "source/story/runtime/chapter-0001.plan.json": "{}",
    "source/story/snapshots/1/current_state.md": "s1",
    "source/story/snapshots/2/current_state.md": "s2",
    "source/story/snapshots/3/current_state.md": "s3",
    "revisions/old/rev-old.md": "old text",
}.items():
    (work / rel).parent.mkdir(parents=True, exist_ok=True)
    (work / rel).write_text(text, encoding="utf-8")
(resume_project / "inkos.json").write_text('{"language":"ko"}', encoding="utf-8")
(resume_project / ".inkos").mkdir()
(resume_project / ".inkos" / "harness.sqlite").write_text("history")
(resume_project / "AGENTS.md").write_text("bridge doc")
chapter_bytes = (work / "source/chapters/0001_시작.md").read_bytes()
(work / "work.json").write_text(json.dumps({"artifacts": [{
    "id": "ch1", "currentRevisionId": "rev-new",
    "revisions": [
        {"id": "rev-old", "path": "source/chapters/0001_시작.md", "snapshotPath": "revisions/old/rev-old.md", "checksum": "sha256:x"},
        {"id": "rev-new", "path": "source/chapters/0001_시작.md", "snapshotPath": "revisions/ch1/rev-new.md",
         "checksum": "sha256:" + hashlib.sha256(chapter_bytes).hexdigest()},
    ]}]}), encoding="utf-8")
resume_out = tmp / "resume.tar.gz"
r = run("pack", str(resume_project), str(resume_out), "--resume")
resume_names = set(tarfile.open(resume_out).getnames())
check("pack --resume keeps settings, manifest, chapters, state and the two newest snapshots",
      {"inkos.json", "works/달빛/work.json", "works/달빛/source/chapters/0001_시작.md", "works/달빛/source/story/state/manifest.json",
       "works/달빛/source/story/snapshots/2/current_state.md", "works/달빛/source/story/snapshots/3/current_state.md"} <= resume_names, str(resume_names))
check("pack --resume leaves out history, search index, runtime, old snapshots and bridge docs",
      not any(n.startswith((".inkos/", "works/달빛/revisions/")) or n.endswith(("memory.db", "AGENTS.md")) or "/runtime/" in n or "/snapshots/1/" in n
              for n in resume_names), str(resume_names))
r = run("unpack", str(resume_out), str(tmp / "resumed"))
rebuilt = tmp / "resumed/works/달빛/revisions/ch1/rev-new.md"
check("unpack rebuilds the current revision snapshot from source when the checksum matches",
      r.returncode == 0 and rebuilt.read_bytes() == chapter_bytes and not (tmp / "resumed/works/달빛/revisions/old/rev-old.md").exists(), r.stdout + r.stderr)

evil = tmp / "evil.tar.gz"
with tarfile.open(evil, "w:gz") as tar:
    info = tarfile.TarInfo("../escape.txt"); data = b"x"; info.size = 1
    import io; tar.addfile(info, io.BytesIO(data))
    info = tarfile.TarInfo("inkos.json"); info.size = 2; tar.addfile(info, io.BytesIO(b"{}"))
run("unpack", str(evil), str(tmp / "evil-dest"))
check("unpack ignores paths outside dest", not (tmp / "escape.txt").exists())

r = run("init-folder", extra={"INKOS_GDRIVE_CLIENT_ID": "cid", "INKOS_GDRIVE_CLIENT_SECRET": "cs", "INKOS_GDRIVE_REFRESH_TOKEN": "fake-refresh"})
check("init-folder creates a folder without a folder id", r.returncode == 0 and "INKOS_GDRIVE_FOLDER_ID=folder1" in r.stdout, r.stdout + r.stderr)
r = run("push", str(project))
check("push without secrets fails clearly", r.returncode == 2 and "INKOS_GDRIVE_REFRESH_TOKEN" in r.stderr, r.stderr)
secrets = {"INKOS_GDRIVE_CLIENT_ID": "cid", "INKOS_GDRIVE_CLIENT_SECRET": "cs", "INKOS_GDRIVE_REFRESH_TOKEN": "fake-refresh", "INKOS_GDRIVE_FOLDER_ID": "folder1"}
for i in range(3):
    r = run("push", str(project), "--keep", "2", extra=secrets)
    check(f"push #{i + 1}", r.returncode == 0 and "uploaded inkos-novel-내-소설-" in r.stdout, r.stdout + r.stderr)
check("push keeps only the newest 2", sum(1 for f in FILES.values() if not f["trashed"]) == 2, str([(f["name"], f["trashed"]) for f in FILES.values()]))
check("token and secrets never printed", all("fake-refresh" not in x and "cs" != x for x in [r.stdout]))
r = run("list", extra=secrets)
check("list shows archives", r.returncode == 0 and r.stdout.count("inkos-novel-") == 2, r.stdout + r.stderr)
r = run("pull", str(tmp / "pulled"), extra=secrets)
check("pull restores the newest archive", r.returncode == 0 and (tmp / "pulled/works/달빛/source/chapters/0001_시작.md").exists(), r.stdout + r.stderr)
import time as _time
# Overwrite protection: two copies of the same work.
copy_b = tmp / "novel"                      # restored under another folder name
r = run("pull", str(copy_b), extra=secrets)
check("pull records the base archive", r.returncode == 0 and (copy_b / ".inkos-drive-base").exists(), r.stdout + r.stderr)
base_b = json.loads((copy_b / ".inkos-drive-base").read_text(encoding="utf-8"))
check("base key comes from the archive name, not the folder", base_b["key"] == "내-소설", str(base_b))
_time.sleep(1.1)
r = run("push", str(project), "--keep", "5", extra=secrets)   # session A pushes again
check("session A push", r.returncode == 0, r.stdout + r.stderr)
_time.sleep(1.1)
r = run("push", str(copy_b), "--keep", "5", extra=secrets)    # session B is now behind
check("push refused when Drive moved past this copy's base", r.returncode == 3 and "another session pushed" in r.stderr, r.stdout + r.stderr)
import shutil as _shutil
r = run("push", str(tmp / "pulled"), "--keep", "5", extra=secrets)   # pulled earlier, now stale too
check("stale pulled copy refused", r.returncode == 3, r.stdout + r.stderr)
_time.sleep(1.1)
r = run("push", str(copy_b), "--keep", "5", "--force", extra=secrets)
check("--force pushes anyway and moves the base", r.returncode == 0 and json.loads((copy_b / ".inkos-drive-base").read_text(encoding="utf-8"))["key"] == "내-소설", r.stdout + r.stderr)
fresh = tmp / "fresh-copy" / "내-소설"
_shutil.copytree(project, fresh, ignore=_shutil.ignore_patterns(".inkos-drive-base"))
r = run("push", str(fresh), "--keep", "5", extra=secrets)
check("copy never restored from Drive is refused when Drive has archives", r.returncode == 3 and "not restored from Drive" in r.stderr, r.stdout + r.stderr)
out2 = tmp / "b.tar.gz"
run("pack", str(copy_b), "-o", str(out2))
check("base marker is not packed", ".inkos-drive-base" not in tarfile.open(out2).getnames())
r = run("pull", str(tmp / "pulled2"), extra={**secrets, "INKOS_GDRIVE_REFRESH_TOKEN": "wrong"})
check("bad refresh token fails", r.returncode != 0 and "HTTP 400" in r.stderr, r.stderr)

server.shutdown()
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
