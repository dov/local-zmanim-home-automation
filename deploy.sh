#!/usr/bin/env bash

# Exit immediately if any command returns a non-zero status
set -e

# Deploys directly out of this git checkout: no files are copied elsewhere.
# Run this script from inside the cloned repo on the target machine
# (e.g. ~/git/local-zmanim-home-automation).
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
MASTER_SCRIPT="shabbat-prepare.py"

# Discover the full path of 'uv'
UV_PATH=$(command -v uv)

# Check if UV_PATH is empty and exit with an error message if it is
if [ -z "$UV_PATH" ]; then
    echo "ERROR: 'uv' command-line tool could not be found."
    echo "Please install it first via: curl -LsSf https://astral.sh | sh"
    exit 1
fi

# Explicitly uses the discovered 'uv' path to execute with the repo's local .venv
CRON_JOB="0 5 * * * cd $REPO_DIR && $UV_PATH run python3 $MASTER_SCRIPT >> $REPO_DIR/shabbat.log 2>&1"

echo "=== Starting Shabbat Automation Deployment (uv edition) ==="

# 1. Safety check: Verify this is actually a git checkout containing the master script
if [ ! -f "$REPO_DIR/$MASTER_SCRIPT" ]; then
    echo "ERROR: $MASTER_SCRIPT not found in $REPO_DIR."
    echo "Please run deploy.sh from inside the git checkout."
    exit 1
fi

# 2. Pull the latest code, if this is a git repo with a remote
if [ -d "$REPO_DIR/.git" ]; then
    echo "Updating git checkout in $REPO_DIR..."
    git -C "$REPO_DIR" pull --ff-only
else
    echo "WARNING: $REPO_DIR is not a git checkout; skipping git pull."
fi

chmod +x "$REPO_DIR"/shabbat-*.py

# 3. Initialize isolated environment via uv, directly inside the repo
echo "Setting up local isolated Python environment via uv..."
cd "$REPO_DIR"

# Create a fresh local virtual environment (.venv) if it doesn't exist
if [ ! -d ".venv" ]; then
    $UV_PATH venv
fi

# Pin dependencies explicitly into the local virtual environment
echo "Installing project dependencies locally..."
$UV_PATH pip install python-crontab zmanim paho-mqtt python-telegram-bot pychromecast

# 4. Idempotent Crontab Injection
echo "Configuring system cron rules..."
# Return home temporarily to safely extract user crontab tracking profile
cd "$HOME"
crontab -l > current_cron.bak 2>/dev/null || touch current_cron.bak

# Drop any older rule that ran the master script out of ~/scripts, then
# check if the current repo-based rule is already registered
sed -i "\#cd .*/scripts && .*$MASTER_SCRIPT#d" current_cron.bak

if grep -Fq "$UV_PATH run python3 $MASTER_SCRIPT" current_cron.bak; then
    echo "Cron entry already exists. Skipping crontab modification."
else
    echo "Appending master schedule trigger to user crontab..."
    echo "$CRON_JOB" >> current_cron.bak
fi
crontab current_cron.bak

# Clean up temporary backup files
rm current_cron.bak

echo "=== Deployment Completed Successfully ==="
echo "The project is isolated inside: $REPO_DIR/.venv/"
echo "The system will check for Shabbat and Yom Tov entry profiles daily at 05:00 AM using '$UV_PATH run'."
