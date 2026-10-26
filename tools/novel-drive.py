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

  novel-drive.py pack  <project> [out.tar.xz | -o out.tar.xz] [--resume] [--gz]
  novel-drive.py unpack <archive> <dest> [--force | --overwrite-work]   # .tar.xz or .tar.gz, detected from the content
  novel-drive.py split <archive> [out_dir] [--part-size 12000]   # parts + <archive>.parts.json
  novel-drive.py join  <archive>.parts.json [-o out.tar.gz]      # checks every sha256
  novel-drive.py push  <project> [--keep 10]      # OAuth push/pull/list/init-folder: 선택, 앱이 쓰지 않음
  novel-drive.py pull  <dest> [--name ARCHIVE_NAME] [--force | --overwrite-work]
  novel-drive.py list
  novel-drive.py init-folder [--name inkos-novels]   # create the archive folder, print its id

Overwrite protection: `pull` records the restored archive in <project>/.inkos-drive-base.
`push` refuses when Drive's newest archive of the same work is not that recorded base
(another session pushed in between, or this copy was never restored from Drive);
`--force` overrides. A successful push records the new archive as the base.

Unpack protection: an existing project needs --force, and --force only overwrites a
freshly initialised project (no work in works/ or books/). When dest already holds a
work or chapter manuscripts, unpack stops with exit 3; --overwrite-work first packs
the whole of dest to <dest>.before-unpack-<UTC>.tar.xz beside it, then overwrites.

Use the narrow `drive.file` OAuth scope: the tool can then see only files it
created, so create the folder with init-folder rather than in the Drive UI.
"""
from __future__ import annotations

import argparse
import hashlib
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


# --resume keeps only what continuing the work needs (see korean-port/RUNTIME.md):
# project settings, each work's manifest, and its source/ (book.json, chapters/,
# story/ with state files and the two newest state snapshots - revising or
# rewriting the newest chapter restores the one before it).
# Left out: .inkos/ (episode history), revisions/ (history; unpack rebuilds the
# current revision's snapshot from source/ when the checksum matches), story/memory.db
# (a rebuildable search index), older snapshots, and the bridge docs the installer writes.
RESUME_ROOT_FILES = {"inkos.json", ".node-version", ".nvmrc"}
RESUME_SKIP_STORY = {"memory.db", "memory.db-shm", "memory.db-wal"}
RESUME_SNAPSHOTS = 2


def resume_paths(project: Path) -> set[str]:
    keep = set(RESUME_ROOT_FILES)
    for manifest_path in sorted((project / "works").glob("*/work.json")):
        keep.add(PurePosixPath("works", manifest_path.parent.name, "work.json").as_posix())
    return keep


def kept_snapshots(project: Path, work: str) -> set[str]:
    root = project / "works" / work / "source" / "story" / "snapshots"
    numbers = sorted((int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()), reverse=True) if root.is_dir() else []
    return {str(n) for n in numbers[:RESUME_SNAPSHOTS]}


def resume_included(project: Path, rel: PurePosixPath, keep: set[str], snapshots: dict[str, set[str]]) -> bool:
    if rel.as_posix() in keep:
        return True
    parts = rel.parts
    if not (len(parts) > 3 and parts[0] == "works" and parts[2] == "source"):
        return False
    story = parts[3:]
    if story[:1] == ("story",) and len(story) == 2 and story[1] in RESUME_SKIP_STORY:
        return False
    if story[:2] == ("story", "snapshots") and len(story) > 2:
        if parts[1] not in snapshots:
            snapshots[parts[1]] = kept_snapshots(project, parts[1])
        return story[2] in snapshots[parts[1]]
    return True


def restore_current_snapshots(dest: Path) -> int:
    """Recreate each current revision's snapshot from its source file (same checksum)."""
    restored = 0
    for manifest_path in sorted((dest / "works").glob("*/work.json")):
        work_dir = manifest_path.parent
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for artifact in manifest.get("artifacts", []):
            for revision in artifact.get("revisions", []):
                snapshot, source = revision.get("snapshotPath"), revision.get("path")
                if revision.get("id") != artifact.get("currentRevisionId") or not snapshot or not source:
                    continue
                target, origin = work_dir / snapshot, work_dir / source
                if target.exists() or not origin.is_file() or ".." in PurePosixPath(snapshot).parts:
                    continue
                data = origin.read_bytes()
                if "sha256:" + hashlib.sha256(data).hexdigest() != revision.get("checksum"):
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                restored += 1
    return restored


def xz_available() -> bool:
    try:
        import lzma  # noqa: F401  (some minimal Python builds lack it)
    except ImportError:
        return False
    return True


def pack_format(output: str | None, force_gz: bool) -> str:
    """xz by default (archives about half the gzip size); gz when asked for, named .tar.gz/.tgz, or when lzma is missing."""
    if force_gz or (output and output.endswith((".tar.gz", ".tgz"))):
        return "gz"
    if not xz_available():
        print("warning: Python lzma module is not available; writing a gzip archive (.tar.gz) instead of .tar.xz", file=sys.stderr)
        return "gz"
    return "xz"


def with_format_suffix(name: str, fmt: str) -> str:
    for suffix in (".tar.xz", ".txz", ".tar.gz", ".tgz"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return f"{name}.tar.{fmt}"


def pack_bytes(project: Path, resume: bool = False, fmt: str = "gz") -> bytes:
    if not (project / "inkos.json").is_file():
        die(f"{project} is not an InkOS project (no inkos.json)")
    keep = resume_paths(project) if resume else set()
    snapshots: dict[str, set[str]] = {}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode=f"w:{fmt}") as tar:
        for path in sorted(project.rglob("*")):
            rel = PurePosixPath(path.relative_to(project).as_posix())
            if path.is_symlink() or not included(rel):
                continue
            if resume and not resume_included(project, rel, keep, snapshots):
                continue
            if path.is_file():
                tar.add(path, arcname=str(rel), recursive=False)
    return buffer.getvalue()


# What makes a project more than a fresh `inkos init`: works (2.0 works/<id>/, whose
# long-form chapters are source/chapters/NNNN_<title>.md and whose script/explainer
# drafts are other files in source/) and 1.8-layout books/<id>/chapters/*.md.
WORK_PATTERNS = ("works/*/work.json", "works/*/source/chapters/*.md", "books/*/chapters/*.md")


def existing_work(dest: Path) -> list[str]:
    found: list[str] = []
    for pattern in WORK_PATTERNS:
        found += [path.relative_to(dest).as_posix() for path in sorted(dest.glob(pattern)) if path.is_file()]
    return found


def backup_before_unpack(dest: Path) -> Path:
    fmt = "xz" if xz_available() else "gz"
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    backup = dest.parent / f"{dest.name}.before-unpack-{stamp}.tar.{fmt}"
    data = pack_bytes(dest, fmt=fmt)
    with open(backup, "xb") as out:  # never replace an earlier backup
        out.write(data)
    return backup


def unpack_bytes(data: bytes, dest: Path, force: bool, overwrite_work: bool = False) -> int:
    if data.startswith(b"\xfd7zXZ\x00") and not xz_available():
        die("this is an xz archive (.tar.xz) but the Python lzma module is not available; "
            "unpack it elsewhere or use `tar -xJf` with the xz tool")
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
            tar.getmembers()
    except (tarfile.TarError, EOFError, OSError) as error:
        die(f"not a readable archive: {error}")
    if (dest / "inkos.json").exists():
        work = existing_work(dest)
        if work and not overwrite_work:
            shown = ", ".join(work[:5]) + (f" and {len(work) - 5} more" if len(work) > 5 else "")
            die(f"{dest} already holds work ({shown}); nothing was changed. --force only overwrites a freshly "
                "initialised project. Stop and ask the user: --overwrite-work first packs the whole of "
                f"{dest} to {dest.name}.before-unpack-<UTC>.tar.xz beside it, then overwrites", 3)
        if not (force or overwrite_work):
            die(f"{dest} already contains a project; pass --force to overwrite files from the archive")
        if overwrite_work:
            backup = backup_before_unpack(dest)
            print(f"backed up {dest} ({len(work)} work files) to {backup} before overwriting; "
                  "it holds the manuscripts, so do not commit or upload it")
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
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
    restore_current_snapshots(dest)
    return count


# ------------------------------------------------------------------- parts
# Drive connectors that take file content inline (base64 in the tool call) cannot
# carry a whole archive, so it goes up in parts with a manifest (see RUNTIME.md).
PART_SIZE = 12000


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_archive(archive: Path, out_dir: Path, part_size: int = PART_SIZE) -> Path:
    data = archive.read_bytes()
    chunks = [data[i:i + part_size] for i in range(0, len(data), part_size)] or [b""]
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        name = f"{archive.name}.part{index}of{len(chunks)}"
        (out_dir / name).write_bytes(chunk)
        parts.append({"name": name, "size": len(chunk), "sha256": sha256_hex(chunk)})
    manifest = out_dir / f"{archive.name}.parts.json"
    manifest.write_text(json.dumps({"archive": archive.name, "size": len(data), "sha256": sha256_hex(data), "parts": parts},
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def join_archive(manifest_path: Path, out: Path | None = None) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    folder = manifest_path.parent
    data = b""
    for part in manifest["parts"]:
        path = folder / PurePosixPath(part["name"]).name
        if not path.is_file():
            die(f"missing part {path.name}")
        chunk = path.read_bytes()
        if len(chunk) != part["size"] or sha256_hex(chunk) != part["sha256"]:
            die(f"part {path.name} does not match the manifest (size or sha256)")
        data += chunk
    if len(data) != manifest["size"] or sha256_hex(data) != manifest["sha256"]:
        die("joined archive does not match the manifest (size or sha256)")
    target = out or folder / PurePosixPath(manifest["archive"]).name
    target.write_bytes(data)
    return target


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
    p.add_argument("--resume", action="store_true", help="only what continuing the work needs (no history)")
    p.add_argument("--gz", action="store_true", help="write gzip (.tar.gz) instead of the default xz")
    p = sub.add_parser("unpack"); p.add_argument("archive"); p.add_argument("dest")
    p.add_argument("--force", action="store_true", help="overwrite a freshly initialised project (no works yet)")
    p.add_argument("--overwrite-work", action="store_true", help="overwrite a project that holds work, after backing it up beside it")
    p = sub.add_parser("split"); p.add_argument("archive"); p.add_argument("out_dir", nargs="?")
    p.add_argument("--part-size", type=int, default=PART_SIZE)
    p = sub.add_parser("join"); p.add_argument("manifest"); p.add_argument("-o", "--output")
    p = sub.add_parser("push"); p.add_argument("project"); p.add_argument("--keep", type=int, default=10)
    p.add_argument("--force", action="store_true", help="push even if Drive's newest archive is not this copy's base")
    p = sub.add_parser("pull"); p.add_argument("dest"); p.add_argument("--name"); p.add_argument("--key", help="work key (archive name part)")
    p.add_argument("--force", action="store_true", help="overwrite a freshly initialised project (no works yet)")
    p.add_argument("--overwrite-work", action="store_true", help="overwrite a project that holds work, after backing it up beside it")
    sub.add_parser("list")
    p = sub.add_parser("init-folder"); p.add_argument("--name", default="inkos-novels")
    args = parser.parse_args(argv)

    if args.command == "pack":
        project = Path(args.project)
        requested = args.output or args.archive
        fmt = pack_format(requested, args.gz)
        data = pack_bytes(project, resume=args.resume, fmt=fmt)
        out = Path(with_format_suffix(requested or archive_name(project_key(project)), fmt))
        out.write_bytes(data)
        print(f"packed {project} -> {out} ({len(data)} bytes)")
    elif args.command == "unpack":
        count = unpack_bytes(Path(args.archive).read_bytes(), Path(args.dest), args.force, args.overwrite_work)
        print(f"unpacked {count} files into {args.dest}")
    elif args.command == "split":
        archive = Path(args.archive)
        manifest = split_archive(archive, Path(args.out_dir or f"{archive}.parts"), args.part_size)
        info = json.loads(manifest.read_text(encoding="utf-8"))
        print(f"split {archive.name} ({info['size']} bytes, sha256 {info['sha256']}) into {len(info['parts'])} parts; manifest {manifest}")
    elif args.command == "join":
        target = join_archive(Path(args.manifest), Path(args.output) if args.output else None)
        print(f"joined {target} (size and sha256 match the manifest)")
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
            count = unpack_bytes(download(token, chosen["id"]), Path(args.dest), args.force, args.overwrite_work)
            write_base(Path(args.dest), chosen["name"], chosen.get("id"))
            print(f"restored {chosen['name']} ({count} files) into {args.dest}; base recorded in {BASE_FILE}")


if __name__ == "__main__":
    main()
