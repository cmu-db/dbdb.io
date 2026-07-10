#!/bin/sh
# Generate a new snapshot about each repository that is still active once a week.
# Or check whether they have been abandoned.
# This has to run on a machine that has storage space for all the collected repos.

LOCKFILE="/run/lock/collect_repos.lock"
exec 9>"$LOCKFILE"
flock --nonblock 9 || { echo "collect_repos.sh: already running, exiting." >&2; exit 1; }

uv run ./manage.py collect_repo_info --debug \
  --check-abandoned \
  --ignore-last-checked=2 \
  --sleep=300
