#!/bin/sh
# This should be run weekly to recompute the "People Who Viewed..."

uv run ./manage.py  process_visits --debug --clear --store \
  --min-visit=75 \
  --max-threshold=45 \
  --min-threshold=4
