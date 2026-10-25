#!/bin/sh
# One-shot setup for the Korean InkOS fork in an agent session
# (Claude Code cloud, Codex cloud, or a local machine used by Grok).
#
#   sh tools/setup-cloud.sh [--project DIR] [--no-build] [--pull]
#
# 1. checks Node 22.16+, installs pnpm if needed, builds the fork
# 2. puts an `inkos` launcher on PATH (~/.local/bin)
# 3. creates the novel project with `inkos init --lang ko` when it is missing.
#    With --pull and INKOS_GDRIVE_* secrets it restores the newest OAuth archive
#    instead; the storage policy asks for the user's confirmation first.
# 4. installs the agent bridge into the project and runs `inkos-agent doctor`
#
# No model API key or remote model endpoint is configured; the session answers
# model calls through tools/inkos-agent-bridge.
set -eu
REPO=$(cd "$(dirname "$0")/.." && pwd)
PROJECT="${INKOS_AGENT_PROJECT:-$REPO/novel}"
BUILD=1; PULL=0
while [ $# -gt 0 ]; do
  case $1 in
    --project) PROJECT=$2; shift 2 ;;
    --no-build) BUILD=0; shift ;;
    --pull) PULL=1; shift ;;
    --no-pull) PULL=0; shift ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
case $PROJECT in /*) ;; *) PROJECT="$PWD/$PROJECT" ;; esac
BIN="$HOME/.local/bin"

say() { printf '[setup] %s\n' "$*"; }

command -v node >/dev/null || { echo "node 22.16+ is required" >&2; exit 1; }
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=16)?0:1)' \
  || { echo "node $(node --version) is too old: the 2.0 fork needs 22.16+" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required (agent bridge)" >&2; exit 1; }

if [ $BUILD -eq 1 ]; then
  if ! command -v pnpm >/dev/null; then
    say "installing pnpm"
    corepack enable >/dev/null 2>&1 && corepack prepare pnpm@9.15.9 --activate >/dev/null 2>&1 || npm install -g pnpm@9.15.9
  fi
  say "installing dependencies and building (pnpm)"
  (cd "$REPO" && pnpm install --frozen-lockfile && pnpm -r build)
fi
[ -f "$REPO/packages/cli/dist/index.js" ] || { echo "build output missing: run without --no-build" >&2; exit 1; }

mkdir -p "$BIN"
cat > "$BIN/inkos" <<EOF
#!/bin/sh
exec node "$REPO/packages/cli/dist/index.js" "\$@"
EOF
chmod +x "$BIN/inkos"
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
# Keep the novel out of the code repository when it lives inside it (Drive is the store).
case $PROJECT in "$REPO"/*) [ -f "$PROJECT/.gitignore" ] && grep -qxF '*' "$PROJECT/.gitignore" || printf '*\n' > "$PROJECT/.gitignore" ;; esac

sh "$REPO/tools/inkos-agent-bridge/install.sh" --project "$PROJECT" >/dev/null
PROFILE="$HOME/.bashrc"
MARK="# inkos-ko setup"
if ! grep -qF "$MARK" "$PROFILE" 2>/dev/null; then
  {
    echo "$MARK"
    echo "export PATH=\"$BIN:\$PATH\" INKOS_BIN=\"$BIN/inkos\" INKOS_LOCALE=ko INKOS_AGENT_PROJECT=\"$PROJECT\""
  } >> "$PROFILE"
fi

say "project: $PROJECT"
"$BIN/inkos-agent" doctor || true
say "next: inkos-agent start, then follow $PROJECT/AGENTS.md"
