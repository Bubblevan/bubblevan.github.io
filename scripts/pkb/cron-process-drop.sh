#!/usr/bin/env bash
# PKB Drop Processor - Cron Runner
# Called by Hermes cron job to process drop files from inbox/drop/{hermes,openclaw,workbuddy}/
# Usage: bash scripts/pkb/cron-process-drop.sh

set -euo pipefail

REPO_ROOT="D:/MyLab/Hugo/bubblevan.github.io"

cd "$REPO_ROOT" || {
    echo "ERROR: Cannot cd to $REPO_ROOT" >&2
    exit 1
}

echo "$(date -Iseconds) - Running process-drop..."
python -m scripts.pkb.cli process-drop
echo "$(date -Iseconds) - Done."
