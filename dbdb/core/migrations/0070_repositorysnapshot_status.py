from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0069_repositoryinfo_repositorysnapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='repositorysnapshot',
            name='status',
            field=models.IntegerField(
                choices=[(0, 'Unknown'), (1, 'Valid'), (2, 'Error'), (3, 'Failed')],
                default=0,
                help_text='Outcome of the snapshot retrieval attempt',
            ),
        ),
    ]
