import django.db.models.deletion
from django.db import migrations, models


def migrate_twitter_handles(apps, schema_editor):
    SystemVersion = apps.get_model('core', 'SystemVersion')
    CitationUrl = apps.get_model('core', 'CitationUrl')
    TWITTER_URL = 'https://twitter.com/'
    for sv in SystemVersion.objects.exclude(twitter_handle='').exclude(twitter_handle=None):
        handle = sv.twitter_handle.lstrip('@')
        if not handle:
            continue
        url = f'{TWITTER_URL}{handle}'
        citation, _ = CitationUrl.objects.get_or_create(url=url)
        sv.twitter_url = citation
        sv.save(update_fields=['twitter_url'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0096_organization_crunchbase_url_systemversion_blog_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemversion',
            name='twitter_url',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='version_twitter_urls',
                to='core.citationurl',
                verbose_name='Twitter/X URL',
            ),
        ),
        migrations.RunPython(migrate_twitter_handles, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='systemversion',
            name='twitter_handle',
        ),
    ]
