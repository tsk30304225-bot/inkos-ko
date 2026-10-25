#!/bin/sh
# Install the agent bridge (Linux, macOS, Codex cloud, Claude Code cloud).
#   sh install.sh --project ~/my-novel [--install-inkos 1.8.0] [--force]
# No API keys are read or written.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PROJECT=""; INKOS_VERSION=""; FORCE=0
while [ $# -gt 0 ]; do
  case $1 in
    --project) PROJECT=$2; shift 2 ;;
    --install-inkos) INKOS_VERSION=$2; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v node >/dev/null || { echo "node 22+ is required" >&2; exit 1; }
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
[ "$NODE_MAJOR" -ge 22 ] || { echo "node $(node --version) is too old: InkOS needs Node 22+ (2.0 source: 22.16+)" >&2; exit 1; }

if [ -n "$INKOS_VERSION" ] && ! command -v inkos >/dev/null; then
  npm install -g "@actalk/inkos@$INKOS_VERSION"
fi
command -v inkos >/dev/null || echo "note: 'inkos' not on PATH; set INKOS_BIN=/path/to/inkos (e.g. a 2.0 source build's packages/cli/dist/index.js)"

BIN="${HOME}/.local/bin"
mkdir -p "$BIN"
if [ -e "$BIN/inkos-agent" ] && [ "$(readlink "$BIN/inkos-agent" 2>/dev/null)" != "$HERE/inkos-agent" ]; then
  echo "refusing to replace existing $BIN/inkos-agent" >&2; exit 1
fi
ln -sf "$HERE/inkos-agent" "$BIN/inkos-agent"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "add to PATH: export PATH=\"$BIN:\$PATH\"" ;; esac

if [ -n "$PROJECT" ]; then
  mkdir -p "$PROJECT/.claude/agents"
  for f in AGENTS.md CLAUDE.md GROK.md .claude/agents/inkos-writer.md .claude/agents/inkos-reviewer.md; do
    dest="$PROJECT/$f"
    if [ -e "$dest" ] && [ $FORCE -eq 0 ] && ! cmp -s "$HERE/$f" "$dest"; then
      cp "$HERE/$f" "$dest.inkos-agent"
      echo "kept your $f; new version written to $f.inkos-agent (merge it by hand)"
    else
      cp "$HERE/$f" "$dest"
    fi
  done
  touch "$PROJECT/.gitignore"
  for line in "runtime/" "inkos.pre-agent.json"; do
    grep -qxF "$line" "$PROJECT/.gitignore" || echo "$line" >> "$PROJECT/.gitignore"
  done
  echo "project ready: $PROJECT (export INKOS_AGENT_PROJECT=$PROJECT)"
fi
"$HERE/inkos-agent" --version >/dev/null && echo "inkos-agent installed. Next: inkos-agent doctor && inkos-agent start"
