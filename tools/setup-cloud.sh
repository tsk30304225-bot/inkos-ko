#!/bin/sh
# One-shot setup for the Korean InkOS fork in an agent session
# (Claude Code cloud, Codex cloud, or a local machine used by Grok).
#
#   sh tools/setup-cloud.sh [--project DIR] [--no-build] [--pull] [--replace]
#
# 1. checks Node 22.16+, builds the fork with pnpm 9.15.9 (the lockfile's
#    version) through tools/pnpm-pin, so nested `pnpm` calls in package scripts
#    use it too; another installed pnpm is not used, and nothing is put on the
#    global PATH or in ~/.local/bin for pnpm
# 2. puts an `inkos` launcher on PATH (~/.local/bin)
# 3. creates the novel project with `inkos init --lang ko` when it is missing.
#    With --pull and INKOS_GDRIVE_* secrets it restores the newest OAuth archive
#    instead; the storage policy asks for the user's confirmation first.
# 4. installs the agent bridge into the project, adds two lines to ~/.bashrc
#    and runs `inkos-agent doctor`
#
# Existing installs: before changing anything it checks ~/.local/bin/inkos,
# ~/.local/bin/inkos-agent and its own block in ~/.bashrc. When any of them
# belongs to another installation it prints what points where and exits 3.
# --replace backs them up to ~/.local/bin/.inkos-ko-backup/<time>/ (undo with
# the restore.sh written there) and replaces them. Files are never written
# through a symbolic link (temporary file + rename). A ~/.bashrc that is a link
# (dotfiles managers) is left alone: the two lines are printed to add by hand.
#
# No model API key or remote model endpoint is configured; the session answers
# model calls through tools/inkos-agent-bridge.
set -eu
REPO=$(cd "$(dirname "$0")/.." && pwd)
PROJECT="${INKOS_AGENT_PROJECT:-$REPO/novel}"
BUILD=1; PULL=0; REPLACE=0
while [ $# -gt 0 ]; do
  case $1 in
    --project) PROJECT=$2; shift 2 ;;
    --no-build) BUILD=0; shift ;;
    --pull) PULL=1; shift ;;
    --no-pull) PULL=0; shift ;;
    --replace) REPLACE=1; shift ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
case $PROJECT in /*) ;; *) PROJECT="$PWD/$PROJECT" ;; esac
BIN="$HOME/.local/bin"
PNPM_VERSION=9.15.9
PROFILE="$HOME/.bashrc"
MARK="# inkos-ko setup"
LAUNCHER="#!/bin/sh
exec node \"$REPO/packages/cli/dist/index.js\" \"\$@\""
AGENT_TARGET="$REPO/tools/inkos-agent-bridge/inkos-agent"
EXPORT_LINE="export PATH=\"$BIN:\$PATH\" INKOS_BIN=\"$BIN/inkos\" INKOS_LOCALE=ko INKOS_AGENT_PROJECT=\"$PROJECT\""

say() { printf '[setup] %s\n' "$*"; }
replace_path() { python3 -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' "$1" "$2"; }
write_file() {  # stdin -> $1 via a temporary file and rename (never through a link); $2 = mode
  tmp=$(mktemp "$(dirname "$1")/.inkos-tmp.XXXXXX")
  cat > "$tmp"
  chmod "${2:-644}" "$tmp"
  replace_path "$tmp" "$1"
}
mode_of() { if [ -f "$1" ]; then python3 -c 'import os, sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o7777)[2:])' "$1"; else echo "$2"; fi; }
describe() { if [ -L "$1" ]; then echo "$1 -> $(readlink "$1")"; elif [ -e "$1" ]; then echo "$1 (file, not a link)"; else echo "$1 (absent)"; fi; }
exists() { [ -e "$1" ] || [ -L "$1" ]; }
# Our ~/.bashrc block: the marker line and the export line after it.
profile_block() { [ -f "$PROFILE" ] && awk -v m="$MARK" '$0 == m { print; if ((getline line) > 0) print line }' "$PROFILE" || true; }

command -v node >/dev/null || { echo "node 22.16+ is required" >&2; exit 1; }
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=16)?0:1)' \
  || { echo "node $(node --version) is too old: the 2.0 fork needs 22.16+" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required (agent bridge)" >&2; exit 1; }

# ---- existing installs: check everything before changing anything
foreign=""
if exists "$BIN/inkos" && { [ -L "$BIN/inkos" ] || [ "$(cat "$BIN/inkos")" != "$LAUNCHER" ]; }; then
  foreign="$foreign
  $(describe "$BIN/inkos")$( [ -L "$BIN/inkos" ] || printf ': %s' "$(grep -m1 '^exec' "$BIN/inkos" 2>/dev/null || echo 'other content')")"
fi
if exists "$BIN/inkos-agent" && [ "$(readlink "$BIN/inkos-agent" 2>/dev/null || true)" != "$AGENT_TARGET" ]; then
  foreign="$foreign
  $(describe "$BIN/inkos-agent")"
fi
if [ ! -L "$PROFILE" ] && [ -n "$(profile_block)" ] && [ "$(profile_block)" != "$MARK
$EXPORT_LINE" ]; then
  foreign="$foreign
  $PROFILE has another inkos-ko block: $(profile_block | tail -n 1)"
fi
if [ -n "$foreign" ]; then
  if [ $REPLACE -eq 0 ]; then
    echo "existing installation found (this setup: $REPO, project $PROJECT):$foreign" >&2
    echo "nothing was changed. Rerun with --replace to back these up and replace them." >&2
    exit 3
  fi
  BACKUP="$BIN/.inkos-ko-backup/$(date -u +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP"
  {
    printf '#!/bin/sh\n# Restore what setup-cloud.sh --replace replaced.\nset -eu\nB=$(cd "$(dirname "$0")" && pwd)\n'
    for item in inkos inkos-agent; do
      if exists "$BIN/$item"; then
        cp -P "$BIN/$item" "$BACKUP/$item"
        printf 'rm -f "%s"; cp -P "$B/%s" "%s"\n' "$BIN/$item" "$item" "$BIN/$item"
      else
        printf 'rm -f "%s"\n' "$BIN/$item"
      fi
    done
    if [ -L "$PROFILE" ]; then
      :  # a linked ~/.bashrc is never changed, so there is nothing to restore
    elif exists "$PROFILE"; then
      cp -P "$PROFILE" "$BACKUP/bashrc"
      printf 'rm -f "%s"; cp -P "$B/bashrc" "%s"\n' "$PROFILE" "$PROFILE"
    else
      printf 'rm -f "%s"\n' "$PROFILE"
    fi
  } > "$BACKUP/restore.sh"
  printf 'replaced on %s by %s:%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REPO" "$foreign" > "$BACKUP/README"
  export INKOS_KO_BACKUP_DIR="$BACKUP"
  say "backed up to $BACKUP (undo: sh $BACKUP/restore.sh)"
fi

# ---- build with the lockfile's pnpm
# tools/pnpm-pin/pnpm goes first on PATH only for these commands: package scripts
# call `pnpm` again (packages/cli prebuild -> `pnpm run prepare:workspace-core`),
# and those nested calls must not reach another installed pnpm either.
if [ $BUILD -eq 1 ]; then
  PIN="$REPO/tools/pnpm-pin"
  INSTALLED=$(pnpm --version 2>/dev/null || echo none)
  INKOS_PNPM_PIN_CMD=$(PATH="$PIN:$PATH" INKOS_PNPM_PIN_SHOW=1 pnpm)
  export INKOS_PNPM_PIN_CMD
  USED=$(PATH="$PIN:$PATH" pnpm --version)
  [ "$USED" = "$PNPM_VERSION" ] || { echo "pnpm-pin chose '$INKOS_PNPM_PIN_CMD' but it reports $USED, not $PNPM_VERSION" >&2; exit 1; }
  say "pnpm: $USED via '$INKOS_PNPM_PIN_CMD' (installed pnpm: $INSTALLED)"
  say "installing dependencies and building"
  # node_modules made by another pnpm version must be reinstalled; there is no
  # terminal to confirm that, so confirm-modules-purge is turned off here.
  (cd "$REPO" && PATH="$PIN:$PATH" pnpm install --frozen-lockfile --config.confirm-modules-purge=false \
    && PATH="$PIN:$PATH" pnpm -r build)
fi
[ -f "$REPO/packages/cli/dist/index.js" ] || { echo "build output missing: run without --no-build" >&2; exit 1; }

mkdir -p "$BIN"
printf '%s\n' "$LAUNCHER" | write_file "$BIN/inkos" 755
export PATH="$BIN:$PATH" INKOS_BIN="$BIN/inkos" INKOS_LOCALE=ko INKOS_AGENT_PROJECT="$PROJECT"

if [ ! -f "$PROJECT/inkos.json" ]; then
  if [ $PULL -eq 1 ] && [ -n "${INKOS_GDRIVE_REFRESH_TOKEN:-}" ] && [ -n "${INKOS_GDRIVE_FOLDER_ID:-}" ]; then
    say "restoring the newest novel archive from Google Drive"
    python3 "$REPO/tools/novel-drive.py" pull "$PROJECT" || say "Drive restore failed; starting a new project instead"
  fi
fi
if [ ! -f "$PROJECT/inkos.json" ]; then
  say "creating a new Korean project at $PROJECT"
  mkdir -p "$(dirname "$PROJECT")"
  (cd "$(dirname "$PROJECT")" && "$BIN/inkos" init "$(basename "$PROJECT")" --lang ko >/dev/null)
fi
# Keep the novel out of the code repository when it lives inside it.
case $PROJECT in "$REPO"/*)
  [ -f "$PROJECT/.gitignore" ] && grep -qxF '*' "$PROJECT/.gitignore" \
    || printf '*\n' | write_file "$PROJECT/.gitignore" "$(mode_of "$PROJECT/.gitignore" 644)" ;;
esac

if [ $REPLACE -eq 1 ]; then
  sh "$REPO/tools/inkos-agent-bridge/install.sh" --project "$PROJECT" --replace >/dev/null
else
  sh "$REPO/tools/inkos-agent-bridge/install.sh" --project "$PROJECT" >/dev/null
fi
# Two lines in ~/.bashrc (marker + export); an old inkos-ko block is replaced,
# the rest and the file's permissions are kept. A linked ~/.bashrc is not touched.
if [ -L "$PROFILE" ]; then
  if [ "$(profile_block)" != "$MARK
$EXPORT_LINE" ]; then
    say "$(describe "$PROFILE"): a link, left unchanged. Add these two lines to it yourself"
    say "(and remove an older '$MARK' line and the line after it, if there is one):"
    printf '%s\n%s\n' "$MARK" "$EXPORT_LINE"
  fi
else
  {
    [ -f "$PROFILE" ] && awk -v m="$MARK" '$0 == m { getline; next } { print }' "$PROFILE"
    echo "$MARK"
    echo "$EXPORT_LINE"
  } | write_file "$PROFILE" "$(mode_of "$PROFILE" 644)"
fi

say "project: $PROJECT"
"$BIN/inkos-agent" doctor || true
say "next: inkos-agent start, then follow $PROJECT/AGENTS.md"
