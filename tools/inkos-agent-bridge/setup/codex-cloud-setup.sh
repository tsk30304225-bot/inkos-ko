#!/bin/sh
# For a Codex cloud environment with this repository attached: paste into its
# "Setup script" (runs with internet before the task). Not checked yet. The
# default Codex path is different: no repository attached, and the task itself
# runs `git clone -b claude/eeum-n0rsol …` and `sh tools/setup-cloud.sh`
# (korean-port/RUNTIME.md "Codex 클라우드").
# Builds the Korean 2.0 fork from this repository, restores the novel from
# Google Drive when INKOS_GDRIVE_* secrets are set, and installs the bridge.
set -eu
sh tools/setup-cloud.sh --project "$PWD/novel"
