#!/bin/bash
# Cron job script to automatically rotate log files
# Add this to crontab: 0 */6 * * * /path/to/backend/cron_rotate_logs.sh

# Change to the backend directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run log rotation
echo "$(date): Starting automatic log rotation..." >> logs/rotation.log
python rotate_logs.py --logs-dir logs >> logs/rotation.log 2>&1
echo "$(date): Log rotation completed" >> logs/rotation.log

# Keep rotation log small too
if [ -f "logs/rotation.log" ]; then
    tail -n 100 logs/rotation.log > logs/rotation.log.tmp
    mv logs/rotation.log.tmp logs/rotation.log
fi
