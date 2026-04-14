#!/bin/bash
# Cron wrapper for the AI Outreach Bot
# Add to crontab: crontab -e
# Run 2x/day at 9:00 and 19:00:
#   0 9,19 * * * /home/user/outreach-bot/run.sh

set -e
cd "$(dirname "$0")"
source .env
python agent.py
