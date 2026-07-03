# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.

1. Never use inline CSS. Always put formatting style in "static/core/css/".
2. Never use custom padding, margins, spacing, displays, and sizes. Prefer to use Bootstrap v5.3 constructs instead.
3. Every Django command should extend `DbdbBaseCommand` found in "dbdb/core/management/base.py".
4. Never run tests on the production database defined in ".env". Always use the test database defined in "dbdb/test_settings.py".
