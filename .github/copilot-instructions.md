## Quick orientation for AI coding agents

This repository is a Django-based "Database of Databases" web app (Django 6.0). Use this file as a compact, actionable guide so code changes are small, safe, and aligned with existing conventions.

Key files and places to inspect
- `manage.py` — standard Django entrypoint (runserver, migrate, test).
- `dbdb/settings.py` — central configuration. Uses `django-environ` and reads a top-level `.env`. Note middleware toggles when `DEBUG` is True.
- `dbdb/core/` — main app. Important modules:
  - `models.py` — domain models `System`, `SystemVersion`, etc.
  - `views.py` — large file with class-based views and many query patterns; prefer following existing view style when adding features.
  - `forms.py` — custom Django forms (look here before adding new form logic).
  - `utils/` — helpers (e.g. `twitter_card.py`, `searchtext.py`, `logos`).
- `templates/` and `dbdb/core/templates/` — HTML + Jinja/Django templates; many pages are composed with small includes (see `templates/components` and `templates/core`).
- `static/` and `static-live/` — static assets. `STATIC_ROOT` is `static-live` (production). Local development uses `STATICFILES_DIRS`.
- `data/fixtures/` and `initial_data/` — fixture JSON and initial datasets used by tests/scripts.
- `deploy/` and `start_dbdb_wsgi_server.sh` — production deployment helpers (used by ops scripts).

Run / dev commands (concrete)
- Setup a venv and install dependencies:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -U -r requirements.txt`
- Database and env:
  - Create a `.env` at repo root with at least `SECRET_KEY` and a `DATABASE_URL` (or use the shipped `data/db.sqlite3` for quick local testing).
  - `python manage.py migrate`
  - `python manage.py createsuperuser` (if needed)
- Run locally:
  - `python manage.py runserver`
  - In production the repo uses `deploy/update_dbdb_app.sh` and `start_dbdb_wsgi_server.sh`.
- Tests:
  - Run Django tests with `python manage.py test`.

Important conventions & gotchas (project-specific)
- Environment-driven config: `dbdb/settings.py` calls `env.read_env(root('.env'))`. Always check `.env` values (especially `DEBUG`, `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`).
- Cache middleware is conditionally removed when `DEBUG` is True — local behavior may differ from CI/prod. Be mindful when changing caching codepaths.
- Search / indexing: an external Xapian install and scripts are referenced (`bin/install_xapian.sh`). Search/indexing code lives under `dbdb/core/common/searchvector` and related utils — changing search-related models or fields likely requires updating searchtext generation (`dbdb/core/utils/searchtext.py`).
- Static assets: `STATIC_ROOT` → `static-live`. Deployment expects collected/placed assets there. Don't assume `collectstatic` is run locally.
- Templates and forms: the project uses `django-bootstrap5` and `easy_thumbnails` conventions. When changing forms, follow existing form classes in `dbdb/core/forms.py` and look at `templates/core/system-form.html` for usage.

Examples of patterns to follow
- Views: use class-based views as in `dbdb/core/views.py` (lots of small helpers and dataclasses). When adding filters, mimic `BrowseView.build_filter_groups`.
- Migrations: update `models.py` and then run `python manage.py makemigrations` and `migrate` — review for cascade effects (System ↔ SystemVersion relations are central).
- Fixtures: seed data lives under `data/fixtures/`; tests and some management commands expect those fixtures.

Where to be conservative (don't change lightly)
- `dbdb/core/models.py` schema and `generate_searchtext` — changes affect search, import scripts, and fixtures.
- Template fragment names and template context keys (many views rely on exact keys such as `activate`, `versions`, `systems`).
- Deployment scripts in `deploy/` and `start_dbdb_wsgi_server.sh` — coordinate with ops if modifying.

Quick checklist for PRs
- Keep changes small and focused.
- Update or add fixture(s) if models change.
- Run `python manage.py test` and confirm no failures.
- Search-related changes: run any local indexer or update `generate_searchtext` to preserve search behavior.

If something is unclear, ask the repo owner for the preferred local dev workflow (DB choice, whether to use the provided `data/db.sqlite3`, and whether collectstatic or Xapian setup is required).

---
If you want, I can iterate on this file to add specific code examples (small snippets) for common edits such as adding a new view + template + URL, or show how to run a minimal local environment using the included `data/db.sqlite3`.
