#!/bin/sh
# Paste into the Codex cloud environment's "Setup script" (runs with internet
# before the task; the task itself needs no internet and no API key).
# Assumes this package is committed to your repo at tools/inkos-agent-bridge and
# the novel project lives at ./my-novel. Adjust both paths.
set -eu
npm install -g @actalk/inkos@1.8.0
[ -f my-novel/inkos.json ] || inkos init my-novel --lang en   # --lang ko needs the Korean patch
sh tools/inkos-agent-bridge/install.sh --project "$PWD/my-novel"
echo 'export PATH="$HOME/.local/bin:$PATH"; export INKOS_AGENT_PROJECT="'"$PWD"'/my-novel"' >> "$HOME/.bashrc"
