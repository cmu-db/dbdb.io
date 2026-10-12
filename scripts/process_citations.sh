#!/bin/sh -x

LOCKFILE="/run/lock/process_citations.lock"
exec 9>"$LOCKFILE"
flock --nonblock 9 || { echo "process_citations.sh: already running, exiting." >&2; exit 1; }

COMMON_ARGS="--debug --normalize --skip-errors"
LAST_CHECKED=$(date -d "2 days ago" +%Y-%m-%d)

# Scan the SystemVersion.system_urls so we can track
uv run ./manage.py process_citations $COMMON_ARGS --ignore=github.com --only=system_url --skip-redirects --sleep=10 --last-checked=$LAST_CHECKED

# First process Github repos without spam checks
uv run ./manage.py process_citations $COMMON_ARGS --only-new --skip-spamcheck github.com --sleep=120
