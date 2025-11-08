#!/bin/bash
# Apply the mounted crontab and start cron daemon
crontab /etc/cron.d/skim-cron
cron && tail -f /var/log/cron.log /app/logs/skim_*.log 2>/dev/null || tail -f /var/log/cron.log
