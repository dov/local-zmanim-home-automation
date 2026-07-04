#!/usr/bin/env bash

# Exit immediately if any command returns a non-zero status
set -e

SCRIPT_DIR="$HOME/scripts"
MASTER_SCRIPT="shabbat-prepare.py"
CRON_JOB="0 5 * * * /usr/bin/python3 $SCRIPT_DIR/$MASTER_SCRIPT >> $SCRIPT_DIR/shabbat.log 2>&1"

echo "=== Starting Shabbat Automation Deployment ==="

# 1. Ensure the correct target directory layout exists
if [ ! -d "$SCRIPT_DIR" ]; then
    echo "Creating directory: $SCRIPT_DIR"
    mkdir -p "$SCRIPT_DIR"
fi

# 2. Safety check: Verify the master script exists in the current folder before copying
if [ ! -f "$MASTER_SCRIPT" ]; then
    echo "ERROR: $MASTER_SCRIPT not found in the current directory."
    echo "Please run deploy.sh from the folder containing your python scripts."
    exit 1
fi

# 3. Clean python package environment setup
echo "Verifying Python dependencies..."
# Ensure the conflicting crontab package is gone, then install the correct engine
pip uninstall -y crontab 2>/dev/null || true
pip install python-crontab zmanim

# 4. Sync automation scripts to the live directory layout
echo "Deploying script assets to $SCRIPT_DIR..."
cp shabbat-*.py "$SCRIPT_DIR/" 2>/dev/null || true

# Apply execution flags securely
chmod +x "$SCRIPT_DIR"/*.py

# 5. Idempotent Crontab Injection
echo "Configuring system cron rules..."
# Backup existing crontab safely
crontab -l > current_cron.bak 2>/dev/null || touch current_cron.bak

# Check if the specific master job rule is already registered
if grep -Fq "$SCRIPT_DIR/$MASTER_SCRIPT" current_cron.bak; then
    echo "Cron entry already exists. Skipping crontab modification."
else
    echo "Appending master schedule trigger to user crontab..."
    echo "$CRON_JOB" >> current_cron.bak
    crontab current_cron.bak
    echo "Crontab updated successfully."
fi

# Clean up temporary storage backup reference
rm current_cron.bak

echo "=== Deployment Completed Successfully ==="
echo "The system will check for Shabbat and Yom Tov entry profiles daily at 05:00 AM."
