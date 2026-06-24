import django.contrib.postgres.fields
from django.db import migrations, models


def populate_array(apps, schema_editor):
    SystemVersion = apps.get_model('core', 'SystemVersion')
    for sv in SystemVersion.objects.exclude(former_names=''):
        names = [n.strip() for n in sv.former_names.split(',') if n.strip()]
        sv.former_names_new = names
        sv.save(update_fields=['former_names_new'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0089_organization_former_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemversion',
            name='former_names_new',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=200),
                blank=True,
                default=list,
            ),
        ),
        migrations.RunPython(populate_array, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='systemversion',
            name='former_names',
        ),
        migrations.RenameField(
            model_name='systemversion',
            old_name='former_names_new',
            new_name='former_names',
        ),
    ]
