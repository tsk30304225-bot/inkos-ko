#!/usr/bin/env python3
"""Keep InkOS novel projects between agent sessions in Google Drive.

Cloud sessions (Claude Code, Codex) lose their container when they end, and
work folders are git-ignored. This tool packs a project into a tar.gz, uploads
it to one Drive folder, and restores the newest archive in the next session.
Standard library only.

Credentials come from environment variables set in the environment's secret
settings - never from the command line or chat:
  INKOS_GDRIVE_CLIENT_ID, INKOS_GDRIVE_CLIENT_SECRET, INKOS_GDRIVE_REFRESH_TOKEN
  INKOS_GDRIVE_FOLDER_ID   (the Drive folder that holds the archives)

  novel-drive.py pack  <project> [out.tar.gz | -o out.tar.gz]
  novel-drive.py unpack <archive> <dest>
  novel-drive.py push  <project> [--keep 10]
  novel-drive.py pull  <dest> [--name ARCHIVE_NAME] [--force]
  novel-drive.py list
  novel-drive.py init-folder [--name inkos-novels]   # create the archive folder, print its id

Overwrite protection: `pull` records the restored archive in <project>/.inkos-drive-base.
`push` refuses when Drive's newest archive of the same work is not that recorded base
(another session pushed in between, or this copy was never restored from Drive);
`--force` overrides. A successful push records the new archive as the base.

Use the narrow `drive.file` OAuth scope: the tool can then see only files it
created, so create the folder with init-folder rather than in the Drive UI.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

PREFIX = "inkos-novel-"
SKIP_DIRS = {"runtime", "node_modules", "__pycache__", ".git"}
BASE_FILE = ".inkos-drive-base"
SKIP_FILES = {".env", ".env.local", BASE_FILE}
# Endpoint overrides exist only for the offline test (tools/tests/test_novel_drive.py).
TOKEN_URL = os.environ.get("INKOS_GDRIVE_TEST_TOKEN_URL", "https://oauth2.googleapis.com/token")
API = os.environ.get("INKOS_GDRIVE_TEST_API", "https://www.googleapis.com/drive/v3")
UPLOAD = os.environ.get("INKOS_GDRIVE_TEST_UPLOAD", "https://www.googleapis.com/upload/drive/v3/files")
ENV = ("INKOS_GDRIVE_CLIENT_ID", "INKOS_GDRIVE_CLIENT_SECRET", "INKOS_GDRIVE_REFRESH_TOKEN", "INKOS_GDRIVE_FOLDER_ID")
AUTH_ENV = ENV[:3]


def die(message: str, code: int = 1):
    print(f"novel-drive: {message}", file=sys.stderr)
    raise SystemExit(code)


# ------------------------------------------------------------------ archive
def included(rel: PurePosixPath) -> bool:
    if any(part in SKIP_DIRS for part in rel.parts[:-1]) or rel.name in SKIP_DIRS:
        return False
    return rel.name not in SKIP_FILES and not rel.name.startswith(".env.")


def pack_bytes(project: Path) -> bytes:
    if not (project / "inkos.json").is_file():
        die(f"{project} is not an InkOS project (no inkos.json)")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in sorted(project.rglob("*")):
            rel = PurePosixPath(path.relative_to(project).as_posix())
            if path.is_symlink() or not included(rel):
                continue
            if path.is_file():
                tar.add(path, arcname=str(rel), recursive=False)
    return buffer.getvalue()


def unpack_bytes(data: bytes, dest: Path, force: bool) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    if (dest / "inkos.json").exists() and not force:
        die(f"{dest} already contains a project; pass --force to overwrite files from the archive")
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            rel = PurePosixPath(member.name)
            if not member.isfile() or rel.is_absolute() or ".." in rel.parts:
                continue  # never write outside dest or create links
            target = dest.joinpath(*rel.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            if source is None:
                continue
            target.write_bytes(source.read())
            count += 1
    return count


# ------------------------------------------------------------------- drive
def credentials(names: tuple[str, ...] = ENV) -> dict[str, str]:
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        die("missing environment variables: " + ", ".join(missing)
            + " (add them in the environment's secret settings; see korean-port/RUNTIME.md)", 2)
    return {name: os.environ[name] for name in names}


def http(method: str, url: str, *, token: str | None = None, data: bytes | None = None,
         headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, data=data, method=method, headers=dict(headers or {}))
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")[:500]
        die(f"{method} {url.split('?')[0]} failed: HTTP {error.code} {body}")


def access_token(creds: dict[str, str]) -> str:
    form = urllib.parse.urlencode({
        "client_id": creds["INKOS_GDRIVE_CLIENT_ID"],
        "client_secret": creds["INKOS_GDRIVE_CLIENT_SECRET"],
        "refresh_token": creds["INKOS_GDRIVE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    _, _, body = http("POST", TOKEN_URL, data=form, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(body)["access_token"]


def list_archives(token: str, folder: str) -> list[dict]:
    query = f"'{folder}' in parents and name contains '{PREFIX}' and trashed = false"
    params = urllib.parse.urlencode({"q": query, "orderBy": "createdTime desc",
                                     "fields": "files(id,name,size,createdTime)", "pageSize": "100"})
    _, _, body = http("GET", f"{API}/files?{params}", token=token)
    return json.loads(body).get("files", [])


def upload(token: str, folder: str, name: str, data: bytes) -> dict:
    metadata = json.dumps({"name": name, "parents": [folder], "mimeType": "application/gzip"}).encode()
    _, headers, _ = http("POST", f"{UPLOAD}?uploadType=resumable&fields=id,name,size", token=token, data=metadata,
                         headers={"Content-Type": "application/json; charset=UTF-8",
                                  "X-Upload-Content-Type": "application/gzip",
                                  "X-Upload-Content-Length": str(len(data))})
    location = headers.get("Location") or headers.get("location")
    if not location:
        die("Drive did not return an upload location")
    _, _, body = http("PUT", location, token=token, data=data, headers={"Content-Type": "application/gzip"})
    return json.loads(body)


def download(token: str, file_id: str) -> bytes:
    return http("GET", f"{API}/files/{file_id}?alt=media", token=token)[2]


# ---------------------------------------------------------------- commands
def archive_name(key: str) -> str:
    return f"{PREFIX}{key}-{time.strftime('%Y%m%d-%H%M%S')}.tar.gz"


def archive_key(name: str) -> str | None:
    """Work key inside an archive name: inkos-novel-<key>-<YYYYMMDD-HHMMSS>.tar.gz."""
    match = re.fullmatch(re.escape(PREFIX) + r"(.+)-\d{8}-\d{6}\.tar\.gz", name)
    return match.group(1) if match else None


def read_base(project: Path) -> dict | None:
    try:
        return json.loads((project / BASE_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def write_base(project: Path, name: str, file_id: str | None) -> None:
    (project / BASE_FILE).write_text(json.dumps({"name": name, "id": file_id, "key": archive_key(name),
                                                  "recordedAt": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False) + "\n",
                                      encoding="utf-8")


def project_key(project: Path) -> str:
    base = read_base(project)
    return (base or {}).get("key") or project.resolve().name


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pack"); p.add_argument("project"); p.add_argument("archive", nargs="?"); p.add_argument("-o", "--output")
    p = sub.add_parser("unpack"); p.add_argument("archive"); p.add_argument("dest"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("push"); p.add_argument("project"); p.add_argument("--keep", type=int, default=10)
    p.add_argument("--force", action="store_true", help="push even if Drive's newest archive is not this copy's base")
    p = sub.add_parser("pull"); p.add_argument("dest"); p.add_argument("--name"); p.add_argument("--key", help="work key (archive name part)")
    p.add_argument("--force", action="store_true")
    sub.add_parser("list")
    p = sub.add_parser("init-folder"); p.add_argument("--name", default="inkos-novels")
    args = parser.parse_args(argv)

    if args.command == "pack":
        project = Path(args.project)
        data = pack_bytes(project)
        out = Path(args.output or args.archive or archive_name(project_key(project)))
        out.write_bytes(data)
        print(f"packed {project} -> {out} ({len(data)} bytes)")
    elif args.command == "unpack":
        count = unpack_bytes(Path(args.archive).read_bytes(), Path(args.dest), args.force)
        print(f"unpacked {count} files into {args.dest}")
    elif args.command == "init-folder":
        token = access_token(credentials(AUTH_ENV))
        _, _, body = http("POST", f"{API}/files?fields=id,name", token=token,
                          data=json.dumps({"name": args.name, "mimeType": "application/vnd.google-apps.folder"}).encode(),
                          headers={"Content-Type": "application/json; charset=UTF-8"})
        folder = json.loads(body)
        print(f"created Drive folder {folder.get('name')}; set INKOS_GDRIVE_FOLDER_ID={folder.get('id')} in the environment secrets")
    else:
        creds = credentials()
        token = access_token(creds)
        folder = creds["INKOS_GDRIVE_FOLDER_ID"]
        if args.command == "list":
            for item in list_archives(token, folder):
                print(f"{item['createdTime']}  {item.get('size', '?'):>10}  {item['name']}")
        elif args.command == "push":
            project = Path(args.project)
            data = pack_bytes(project)
            key = project_key(project)
            same = [item for item in list_archives(token, folder) if archive_key(item["name"]) == key]
            base = read_base(project)
            if same and not args.force:
                latest = same[0]["name"]
                if base is None:
                    die(f"Drive already has archives of '{key}' (newest {latest}) but this copy was not restored from Drive; "
                        "pull first, or pass --force to upload anyway", 3)
                if base.get("name") != latest:
                    die(f"Drive's newest archive of '{key}' is {latest}, but this copy is based on {base.get('name')}; "
                        "another session pushed in between. Pull and merge first, or pass --force to upload anyway", 3)
            name = archive_name(key)
            uploaded = upload(token, folder, name, data)
            write_base(project, uploaded.get("name", name), uploaded.get("id"))
            print(f"uploaded {uploaded.get('name', name)} ({len(data)} bytes, id {uploaded.get('id')})")
            same = [item for item in list_archives(token, folder) if archive_key(item["name"]) == key]
            for old in same[max(args.keep, 1):]:
                http("PATCH", f"{API}/files/{old['id']}", token=token, data=json.dumps({"trashed": True}).encode(),
                     headers={"Content-Type": "application/json"})
                print(f"moved old archive to trash: {old['name']}")
        elif args.command == "pull":
            archives = list_archives(token, folder)
            if args.name:
                archives = [item for item in archives if item["name"] == args.name]
            key = args.key or (read_base(Path(args.dest)) or {}).get("key")
            if key:
                archives = [item for item in archives if archive_key(item["name"]) == key]
            if not archives:
                die("no archive found in the Drive folder")
            chosen = archives[0]
            count = unpack_bytes(download(token, chosen["id"]), Path(args.dest), args.force)
            write_base(Path(args.dest), chosen["name"], chosen.get("id"))
            print(f"restored {chosen['name']} ({count} files) into {args.dest}; base recorded in {BASE_FILE}")


if __name__ == "__main__":
    main()
