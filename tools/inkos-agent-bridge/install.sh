#!/bin/sh
# Install the agent bridge (Linux, macOS, Codex cloud, Claude Code cloud).
#   sh install.sh --project ~/my-novel [--locale ko] [--install-inkos 1.8.0] [--force] [--replace]
# No API keys are read or written.
#
# Files are never written through a symbolic link: each one is written to a
# temporary file and renamed over the target, which replaces a link itself and
# leaves whatever it pointed to untouched. An existing ~/.local/bin/inkos-agent
# that is not this bridge's link stops the install (exit 3); --replace backs it
# up to ~/.local/bin/.inkos-ko-backup/<time>/ (with restore.sh) and replaces it.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PROJECT=""; LOCALE=""; INKOS_VERSION=""; FORCE=0; REPLACE=0
while [ $# -gt 0 ]; do
  case $1 in
    --project) PROJECT=$2; shift 2 ;;
    --install-inkos) INKOS_VERSION=$2; shift 2 ;;
    --force) FORCE=1; shift ;;
    --replace) REPLACE=1; shift ;;
    --locale) LOCALE=$2; shift 2
      case $LOCALE in ''|*[!A-Za-z_-]*) echo "invalid --locale '$LOCALE'" >&2; exit 2 ;; esac ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v node >/dev/null || { echo "node 22+ is required" >&2; exit 1; }
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
[ "$NODE_MAJOR" -ge 22 ] || { echo "node $(node --version) is too old: InkOS needs Node 22+ (2.0 source: 22.16+)" >&2; exit 1; }

# rename(2) replaces the path itself, never the file a link points to.
replace_path() { python3 -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' "$1" "$2"; }
# Copy (or build from stdin when $1 is -) into a temporary file next to $2, then rename it over $2.
write_file() {
  tmp=$(mktemp "$(dirname "$2")/.inkos-tmp.XXXXXX")
  if [ "$1" = - ]; then cat > "$tmp"; else cat "$1" > "$tmp"; fi
  chmod "${3:-644}" "$tmp"
  replace_path "$tmp" "$2"
}
mode_of() { if [ -f "$1" ]; then python3 -c 'import os, sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o7777)[2:])' "$1"; else echo "$2"; fi; }
describe() { if [ -L "$1" ]; then echo "$1 -> $(readlink "$1")"; elif [ -e "$1" ]; then echo "$1 (file, not a link)"; else echo "$1 (absent)"; fi; }

if [ -n "$INKOS_VERSION" ] && ! command -v inkos >/dev/null; then
  npm install -g "@actalk/inkos@$INKOS_VERSION"
fi
command -v inkos >/dev/null || echo "note: 'inkos' not on PATH; set INKOS_BIN=/path/to/inkos (e.g. a 2.0 source build's packages/cli/dist/index.js)"

BIN="${HOME}/.local/bin"
mkdir -p "$BIN"
AGENT="$BIN/inkos-agent"
if { [ -e "$AGENT" ] || [ -L "$AGENT" ]; } && [ "$(readlink "$AGENT" 2>/dev/null || true)" != "$HERE/inkos-agent" ]; then
  if [ $REPLACE -eq 0 ]; then
    echo "existing installation found: $(describe "$AGENT")" >&2
    echo "this bridge would link $AGENT -> $HERE/inkos-agent; rerun with --replace to back it up and replace it" >&2
    exit 3
  fi
  BACKUP="${INKOS_KO_BACKUP_DIR:-$BIN/.inkos-ko-backup/$(date -u +%Y%m%d-%H%M%S)}"
  mkdir -p "$BACKUP"
  cp -P "$AGENT" "$BACKUP/inkos-agent"
  describe "$AGENT" >> "$BACKUP/README"
  if [ -z "${INKOS_KO_BACKUP_DIR:-}" ]; then
    printf '#!/bin/sh\n# Restore what install.sh --replace replaced.\nset -eu\nB=$(cd "$(dirname "$0")" && pwd)\n' > "$BACKUP/restore.sh"
    printf 'rm -f "%s"; cp -P "$B/inkos-agent" "%s"\n' "$AGENT" "$AGENT" >> "$BACKUP/restore.sh"
    echo "backed up $(describe "$AGENT") to $BACKUP (undo: sh $BACKUP/restore.sh)"
  fi
fi
tmp_link="$BIN/.inkos-agent.tmp.$$"
rm -f "$tmp_link"
ln -s "$HERE/inkos-agent" "$tmp_link"
replace_path "$tmp_link" "$AGENT"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "add to PATH: export PATH=\"$BIN:\$PATH\"" ;; esac

if [ -n "$PROJECT" ]; then
  mkdir -p "$PROJECT/.claude/agents"
  PROJECT=$(cd "$PROJECT" && pwd)
  for f in AGENTS.md CLAUDE.md GROK.md .claude/agents/inkos-writer.md .claude/agents/inkos-reviewer.md; do
    dest="$PROJECT/$f"
    if [ -e "$dest" ] && [ $FORCE -eq 0 ] && ! cmp -s "$HERE/$f" "$dest"; then
      write_file "$HERE/$f" "$dest.inkos-agent"
      echo "kept your $f; new version written to $f.inkos-agent (merge it by hand)"
    else
      write_file "$HERE/$f" "$dest"
    fi
  done
  {
    [ -f "$PROJECT/.gitignore" ] && cat "$PROJECT/.gitignore"
    for line in "runtime/" "inkos.pre-agent.json"; do
      grep -qxF "$line" "$PROJECT/.gitignore" 2>/dev/null || echo "$line"
    done
  } | write_file - "$PROJECT/.gitignore" "$(mode_of "$PROJECT/.gitignore" 644)"
  # Record the project for inkos-agent, so shells without INKOS_AGENT_PROJECT (Codex opens
  # a new shell per command and does not read ~/.bashrc) still find it. runtime/ is git-ignored.
  STATE_DIR="${INKOS_AGENT_STATE:-$HERE/runtime}"
  mkdir -p "$STATE_DIR"
  printf '%s\n' "$PROJECT" | write_file - "$STATE_DIR/project"
  echo "project ready: $PROJECT (recorded in $STATE_DIR/project)"
fi
if [ -n "$LOCALE" ]; then
  # The CLI language for InkOS jobs when INKOS_LOCALE is not set in that shell.
  STATE_DIR="${INKOS_AGENT_STATE:-$HERE/runtime}"
  mkdir -p "$STATE_DIR"
  printf '%s\n' "$LOCALE" | write_file - "$STATE_DIR/locale"
  echo "locale recorded: $LOCALE (in $STATE_DIR/locale)"
fi
"$HERE/inkos-agent" --version >/dev/null && echo "inkos-agent installed. Next: inkos-agent doctor && inkos-agent start"
