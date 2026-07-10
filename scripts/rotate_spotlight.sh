#!/bin/sh
# Rotate the homepage spotlight system to a new eligible entry once per week.
# Suggested cron entry (Monday midnight):
#   0 0 * * 1  cd /path/to/web && ./scripts/rotate_spotlight.sh >> /var/log/dbdb/rotate_spotlight.log 2>&1

LOCKFILE="/run/lock/rotate_spotlight.lock"
exec 9>"$LOCKFILE"
flock --nonblock 9 || { echo "rotate_spotlight.sh: already running, exiting." >&2; exit 1; }

uv run ./manage.py rotate_spotlight
