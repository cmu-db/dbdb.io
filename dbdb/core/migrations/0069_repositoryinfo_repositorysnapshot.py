import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0068_systemversion_foundation'),
    ]

    operations = [
        # RepositoryInfo first, without the circular `current` FK
        migrations.CreateModel(
            name='RepositoryInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('last_snapshot', models.DateTimeField(
                    blank=True, null=True,
                    help_text='Timestamp of the last time this repository was scanned')),
                ('enabled', models.BooleanField(
                    default=True,
                    help_text='Whether this repository should be scanned for new snapshots')),
                ('sourcerepo_url', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='repository_info',
                    to='core.citationurl',
                    verbose_name='Source Repository URL')),
            ],
            options={
                'verbose_name': 'Repository Info',
                'verbose_name_plural': 'Repository Infos',
            },
        ),
        # RepositorySnapshot with FK back to RepositoryInfo
        migrations.CreateModel(
            name='RepositorySnapshot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('commit_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Total number of commits on the default branch')),
                ('last_commit_timestamp', models.DateTimeField(
                    blank=True, null=True,
                    help_text='Timestamp of the most recent commit')),
                ('last_commit_hash', models.CharField(
                    blank=True, max_length=64,
                    help_text='SHA hash of the most recent commit')),
                ('open_pr_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Number of currently open pull requests / merge requests')),
                ('merged_pr_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Total number of merged pull requests / merge requests')),
                ('last_pr_submitted_at', models.DateTimeField(
                    blank=True, null=True,
                    help_text='Timestamp of the most recently submitted (opened) pull request')),
                ('last_pr_closed_at', models.DateTimeField(
                    blank=True, null=True,
                    help_text='Timestamp of the most recently closed or merged pull request')),
                ('open_issue_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Number of currently open issues')),
                ('closed_issue_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Total number of closed issues')),
                ('last_issue_submitted_at', models.DateTimeField(
                    blank=True, null=True,
                    help_text='Timestamp of the most recently submitted (opened) issue')),
                ('last_issue_closed_at', models.DateTimeField(
                    blank=True, null=True,
                    help_text='Timestamp of the most recently closed issue')),
                ('fork_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Number of repository forks')),
                ('star_count', models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text='Number of repository stars / watchers')),
                ('commit_authors', models.JSONField(
                    blank=True, default=list,
                    help_text='Unique contributor login names or display names (from commit history)')),
                ('pr_authors', models.JSONField(
                    blank=True, default=list,
                    help_text='Unique authors who have submitted pull requests or merge requests')),
                ('issue_authors', models.JSONField(
                    blank=True, default=list,
                    help_text='Unique authors who have submitted issues')),
                ('repo', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='snapshots',
                    to='core.repositoryinfo')),
            ],
            options={
                'verbose_name': 'Repository Snapshot',
                'ordering': ('-created',),
            },
        ),
        # Add the circular FK from RepositoryInfo to RepositorySnapshot
        migrations.AddField(
            model_name='repositoryinfo',
            name='current',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='core.repositorysnapshot',
                verbose_name='Current Snapshot'),
        ),
    ]
