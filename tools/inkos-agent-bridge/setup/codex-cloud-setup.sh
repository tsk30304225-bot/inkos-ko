#!/bin/sh
# Paste into the Codex cloud environment's "Setup script" (runs with internet
# before the task; the task itself needs no internet and no model API key).
# Builds the Korean 2.0 fork from this repository, restores the novel from
# Google Drive when INKOS_GDRIVE_* secrets are set, and installs the bridge.
set -eu
sh tools/setup-cloud.sh --project "$PWD/novel"
