#!/bin/sh

COMMON_ARGS="--debug --normalize --skip-errors --sleep=30"

# First process Github repos without spam checks
uv run ./manage.py process_citations $COMMON_ARGS --only-new --skip-spamcheck github.com

# Then scan the rest
