"""Fix Attribute.sv_field values after 0061 renamed the SystemVersion M2M fields."""
from django.db import migrations

MAPPING = {
    'attr_licenses':      'licenses',
    'attr_oses':          'oses',
    'attr_written_in':    'written_in',
    'attr_project_types': 'project_types',
    'attr_tags':          'tags',
}


def update_sv_fields(apps, schema_editor):
    Attribute = apps.get_model('core', 'Attribute')
    for old, new in MAPPING.items():
        Attribute.objects.filter(sv_field=old).update(sv_field=new)


def reverse_sv_fields(apps, schema_editor):
    Attribute = apps.get_model('core', 'Attribute')
    for old, new in MAPPING.items():
        Attribute.objects.filter(sv_field=new).update(sv_field=old)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0061_remove_legacy_attribute_models'),
    ]

    operations = [
        migrations.RunPython(update_sv_fields, reverse_sv_fields),
    ]