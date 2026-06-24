from django.contrib.postgres.fields import ArrayField
from django.db import migrations, models


class Migration(migrations.Migration):
    # DDL + DML mix (ADD COLUMN then UPDATE then DROP COLUMN) triggers a
    # PostgreSQL "pending trigger events" error inside a transaction, so
    # each statement runs in autocommit mode instead.
    atomic = False

    dependencies = [
        ('core', '0085_repositorysnapshot_archival_timestamp'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name='repositorysnapshot',
                    old_name='branch_name',
                    new_name='branch_names',
                ),
                migrations.AlterField(
                    model_name='repositorysnapshot',
                    name='branch_names',
                    field=ArrayField(
                        models.CharField(max_length=255),
                        default=list, blank=True,
                        help_text="Names of up to 100 branches (most recent / alphabetical order)"),
                ),
                migrations.AlterField(
                    model_name='repositorysnapshot',
                    name='commit_authors',
                    field=ArrayField(
                        models.CharField(max_length=254),
                        default=list, blank=True,
                        help_text="Unique contributor login names or display names (from commit history)"),
                ),
                migrations.AlterField(
                    model_name='repositorysnapshot',
                    name='pr_authors',
                    field=ArrayField(
                        models.CharField(max_length=255),
                        default=list, blank=True,
                        help_text="Unique authors who have submitted pull requests or merge requests"),
                ),
                migrations.AlterField(
                    model_name='repositorysnapshot',
                    name='issue_authors',
                    field=ArrayField(
                        models.CharField(max_length=255),
                        default=list, blank=True,
                        help_text="Unique authors who have submitted issues"),
                ),
            ],
            # ALTER COLUMN ... USING does not support subqueries in PostgreSQL,
            # so we use add-new-column + UPDATE + drop-old + rename instead.
            database_operations=[
                # branch_name → branch_names (rename + jsonb → varchar[])
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN branch_names varchar(255)[] NOT NULL DEFAULT '{}'",
                        "UPDATE core_repositorysnapshot SET branch_names = ARRAY(SELECT jsonb_array_elements_text(COALESCE(branch_name, '[]'::jsonb)))",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN branch_name",
                    ],
                    reverse_sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN branch_name jsonb NOT NULL DEFAULT '[]'",
                        "UPDATE core_repositorysnapshot SET branch_name = to_jsonb(branch_names)",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN branch_names",
                    ],
                ),
                # commit_authors: jsonb → varchar(254)[]
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN commit_authors_new varchar(254)[] NOT NULL DEFAULT '{}'",
                        "UPDATE core_repositorysnapshot SET commit_authors_new = ARRAY(SELECT jsonb_array_elements_text(COALESCE(commit_authors, '[]'::jsonb)))",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN commit_authors",
                        "ALTER TABLE core_repositorysnapshot RENAME COLUMN commit_authors_new TO commit_authors",
                    ],
                    reverse_sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN commit_authors_old jsonb NOT NULL DEFAULT '[]'",
                        "UPDATE core_repositorysnapshot SET commit_authors_old = to_jsonb(commit_authors)",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN commit_authors",
                        "ALTER TABLE core_repositorysnapshot RENAME COLUMN commit_authors_old TO commit_authors",
                    ],
                ),
                # pr_authors: jsonb → varchar(255)[]
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN pr_authors_new varchar(255)[] NOT NULL DEFAULT '{}'",
                        "UPDATE core_repositorysnapshot SET pr_authors_new = ARRAY(SELECT jsonb_array_elements_text(COALESCE(pr_authors, '[]'::jsonb)))",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN pr_authors",
                        "ALTER TABLE core_repositorysnapshot RENAME COLUMN pr_authors_new TO pr_authors",
                    ],
                    reverse_sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN pr_authors_old jsonb NOT NULL DEFAULT '[]'",
                        "UPDATE core_repositorysnapshot SET pr_authors_old = to_jsonb(pr_authors)",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN pr_authors",
                        "ALTER TABLE core_repositorysnapshot RENAME COLUMN pr_authors_old TO pr_authors",
                    ],
                ),
                # issue_authors: jsonb → varchar(255)[]
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN issue_authors_new varchar(255)[] NOT NULL DEFAULT '{}'",
                        "UPDATE core_repositorysnapshot SET issue_authors_new = ARRAY(SELECT jsonb_array_elements_text(COALESCE(issue_authors, '[]'::jsonb)))",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN issue_authors",
                        "ALTER TABLE core_repositorysnapshot RENAME COLUMN issue_authors_new TO issue_authors",
                    ],
                    reverse_sql=[
                        "ALTER TABLE core_repositorysnapshot ADD COLUMN issue_authors_old jsonb NOT NULL DEFAULT '[]'",
                        "UPDATE core_repositorysnapshot SET issue_authors_old = to_jsonb(issue_authors)",
                        "ALTER TABLE core_repositorysnapshot DROP COLUMN issue_authors",
                        "ALTER TABLE core_repositorysnapshot RENAME COLUMN issue_authors_old TO issue_authors",
                    ],
                ),
            ],
        ),
    ]
