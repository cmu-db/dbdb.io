#!/bin/sh
# Check if any abandoned repo has come back to life! Run this once a month!
# This has to run on a machine that has storage space for all the collected repos.

LOCKFILE="/run/lock/collect_repos.lock"
exec 9>"$LOCKFILE"
flock --nonblock 9 || { echo "collect_repos.sh: already running, exiting." >&2; exit 1; }

uv run ./manage.py collect_repo_info --debug \
  --check-resurrection \
  --ignore-last-checked=14 \
  --sleep=180 \
  github.com
