#!/bin/sh
# This should be run weekly to recompute the "People Who Viewed..."

LOCKFILE="/run/lock/process_visits.lock"
exec 9>"$LOCKFILE"
flock --nonblock 9 || { echo "process_visits.sh: already running, exiting." >&2; exit 1; }

uv run ./manage.py  process_visits --debug --clear --store \
  --min-visit=75 \
  --max-threshold=45 \
  --min-threshold=4
