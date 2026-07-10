#!/bin/sh

LOCKFILE="/run/lock/process_citations.lock"
exec 9>"$LOCKFILE"
flock --nonblock 9 || { echo "process_citations.sh: already running, exiting." >&2; exit 1; }

COMMON_ARGS="--debug --normalize --skip-errors --sleep=30"

# First process Github repos without spam checks
uv run ./manage.py process_citations $COMMON_ARGS --only-new --skip-spamcheck github.com

# Then scan the rest
