from django.db import migrations

FEATURE_CATEGORIES = {
    'Checkpoints':            3,
    'Compression':            1,
    'Concurrency Control':    3,
    'Coordination':           4,
    'Data Model':             1,
    'Fault Tolerance':        4,
    'Foreign Keys':           3,
    'Hardware Acceleration':  4,
    'Indexes':                1,
    'Isolation Levels':       3,
    'Joins':                  2,
    'Logging':                3,
    'Parallel Execution':     2,
    'Query Compilation':      2,
    'Query Execution':        2,
    'Query Interface':        2,
    'Storage Architecture':   1,
    'Storage Format':         1,
    'Storage Model':          1,
    'Storage Organization':   1,
    'Stored Procedures':      2,
    'System Architecture':    4,
    'User-Defined Functions': 2,
    'Views':                  2,
}


def populate_categories(apps, schema_editor):
    Feature = apps.get_model('core', 'Feature')
    for label, category in FEATURE_CATEGORIES.items():
        Feature.objects.filter(label=label).update(category=category)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0080_docs_model_fields'),
    ]

    operations = [
        migrations.RunPython(populate_categories, migrations.RunPython.noop),
    ]
