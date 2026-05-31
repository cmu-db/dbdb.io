from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0070_repositorysnapshot_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='repositorysnapshot',
            name='branch_count',
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text='Total number of branches in the repository',
            ),
        ),
        migrations.AddField(
            model_name='repositorysnapshot',
            name='branch_default_name',
            field=models.CharField(
                blank=True, max_length=255,
                help_text="Name of the repository's default branch",
            ),
        ),
        migrations.AddField(
            model_name='repositorysnapshot',
            name='branch_name',
            field=models.JSONField(
                blank=True, default=list,
                help_text='Names of up to 100 branches (most recent / alphabetical order)',
            ),
        ),
    ]
