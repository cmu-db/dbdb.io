[![Tests](https://github.com/cmu-db/dbdb.io/actions/workflows/tests.yml/badge.svg)](https://github.com/cmu-db/dbdb.io/actions/workflows/tests.yml)

# Database of Databases

## Installation

```bash
sudo apt-get install build-essential libffi-dev libpq-dev python3-dev postgresql-common-dev libcairo2
uv sync
```

## Running the development server

```bash
uv run python manage.py runserver
```

## Deployment

Run `deploy/update_dbdb_app.sh` on the production machine to fetch new changes, run migrations, and restart the wsgi server.

---

## Test fixtures

Test fixtures live in `data/fixtures/`. Django loads them by name; the search path is configured in `settings.py` via `FIXTURE_DIRS`.

| Fixture | Contents | Source |
|---|---|---|
| `adminuser.json` | Superuser account for tests | Static |
| `testuser.json` | Non-superuser account for tests | Static |
| `core_features.json` | `Feature` + `FeatureOption` rows | Dumped from production (see below) |
| `core_attributes.json` | `Attribute` + `AttributeOption` rows | Dumped from production (see below) |
| `core_system.json` | Two synthetic test systems (SQLite, XXX) | Static |
| `core_savedsearch.json` | One saved search for testing | Static |

### Regenerating fixtures from production

Requires Tailscale to be connected so `db-web.tail5fc291.ts.net` is reachable.

```bash
# Features and feature options
uv run python manage.py dumpdata core.feature core.featureoption \
    --indent 2 -o data/fixtures/core_features.json

# Attributes and attribute options
uv run python manage.py dumpdata core.attribute core.attributeoption \
    --indent 2 -o data/fixtures/core_attributes.json
```

These commands use the `DATABASE_URL` in `.env`, which points to the production database.

### Loading fixtures into a local database

```bash
uv run python manage.py loaddata adminuser testuser \
    core_features core_attributes core_system core_savedsearch
```

---

## Running the tests

Tests require a local PostgreSQL instance. The test runner creates and destroys a dedicated database (`test_dbdb_io`) on every run.

```bash
PGUSER=<your-local-pg-user> uv run python manage.py test dbdb.core \
    --settings=dbdb.test_settings --verbosity=2
```

The `dbdb.test_settings` module overrides the production `DATABASE_URL` with local PostgreSQL connection parameters. It reads the following environment variables (all optional, with defaults shown):

| Variable | Default | Notes |
|---|---|---|
| `PGUSER` | `dbdb_user` | Must have `CREATEDB` privilege |
| `PGPASSWORD` | *(empty)* | Omit if using peer auth (Unix socket) |
| `PGHOST` | *(empty)* | Empty = Unix socket (peer auth); `localhost` = TCP |
| `PGPORT` | `5432` | |
| `PGDATABASE` | `postgres` | Connection database — must differ from `test_dbdb_io` |

The test database is always named `test_dbdb_io` and is dropped and recreated fresh on every run.
