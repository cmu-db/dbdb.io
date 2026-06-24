import django.db.models.deletion
from django.db import migrations, models


def migrate_linkedin_handles(apps, schema_editor):
    from django.conf import settings
    SystemVersion = apps.get_model('core', 'SystemVersion')
    CitationUrl = apps.get_model('core', 'CitationUrl')
    base = getattr(settings, 'LINKEDIN_URL', 'https://www.linkedin.com/').rstrip('/')
    for sv in SystemVersion.objects.exclude(linkedin_handle='').exclude(linkedin_handle__isnull=True):
        url = base + '/' + sv.linkedin_handle.lstrip('/')
        citation, _ = CitationUrl.objects.get_or_create(url=url)
        sv.linkedin_url = citation
        sv.save(update_fields=['linkedin_url'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0086_repositorysnapshot_array_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemversion',
            name='linkedin_url',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='version_linkedin_urls',
                to='core.citationurl',
                verbose_name='LinkedIn URL',
            ),
        ),
        migrations.RunPython(migrate_linkedin_handles, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='systemversion',
            name='linkedin_handle',
        ),
    ]
