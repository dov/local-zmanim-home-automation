#!/usr/bin/env bash

# Exit immediately if any command returns a non-zero status
set -e

SCRIPT_DIR="$HOME/scripts"
MASTER_SCRIPT="shabbat-prepare.py"

# Discover the full path of 'uv'
UV_PATH=$(command -v uv)

# Check if UV_PATH is empty and exit with an error message if it is
if [ -z "$UV_PATH" ]; then
    echo "ERROR: 'uv' command-line tool could not be found."
    echo "Please install it first via: curl -LsSf https://astral.sh | sh"
    exit 1
fi

# Explicitly uses the discovered 'uv' path inside your scripts directory to execute with the local .venv
CRON_JOB="0 5 * * * cd $SCRIPT_DIR && $UV_PATH run python3 $MASTER_SCRIPT >> $SCRIPT_DIR/shabbat.log 2>&1"

echo "=== Starting Shabbat Automation Deployment (uv edition) ==="

# 2. Ensure the target directory layout exists
if [ ! -d "$SCRIPT_DIR" ]; then
    echo "Creating directory: $SCRIPT_DIR"
    mkdir -p "$SCRIPT_DIR"
fi

# 3. Safety check: Verify the master script exists locally
if [ ! -f "$MASTER_SCRIPT" ]; then
    echo "ERROR: $MASTER_SCRIPT not found in the current directory."
    echo "Please run deploy.sh from the folder containing your python scripts."
    exit 1
fi

# 4. Sync script assets to the deployment directory
echo "Deploying script assets to $SCRIPT_DIR..."
cp shabbat-*.py "$SCRIPT_DIR/" 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.py

# 5. Initialize isolated environment via uv
echo "Setting up local isolated Python environment via uv..."
cd "$SCRIPT_DIR"

# Create a fresh local virtual environment (.venv) if it doesn't exist
if [ ! -d ".venv" ]; then
    $UV_PATH venv
fi

# Pin dependencies explicitly into the local virtual environment
echo "Installing project dependencies locally..."
$UV_PATH pip install python-crontab zmanim

# 6. Idempotent Crontab Injection
echo "Configuring system cron rules..."
# Return home temporarily to safely extract user crontab tracking profile
cd "$HOME"
crontab -l > current_cron.bak 2>/dev/null || touch current_cron.bak

# Check if the specific uv execution master rule is already registered
if grep -Fq "$UV_PATH run python3 $MASTER_SCRIPT" current_cron.bak; then
    echo "Cron entry already exists. Skipping crontab modification."
else
    echo "Appending master schedule trigger to user crontab..."
    echo "$CRON_JOB" >> current_cron.bak
    crontab current_cron.bak
    echo "Crontab updated successfully."
fi

# Clean up temporary backup files
rm current_cron.bak

echo "=== Deployment Completed Successfully ==="
echo "The project is isolated inside: $SCRIPT_DIR/.venv/"
echo "The system will check for Shabbat and Yom Tov entry profiles daily at 05:00 AM using '$UV_PATH run'."
