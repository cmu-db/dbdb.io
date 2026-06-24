from django.db import migrations


STOCK_EXCHANGES = [
    ('nyse',      'NYSE'),
    ('nasdaq',    'NASDAQ'),
    ('lse',       'LSE'),
    ('tse',       'TSE'),
    ('hkex',      'HKEX'),
    ('asx',       'ASX'),
    ('tsx',       'TSX'),
    ('euronext',  'Euronext'),
    ('other',     'Other'),
]

ORG_TYPES = [
    ('company',      'Company'),
    ('university',   'University'),
    ('individual',   'Individual'),
    ('research-lab', 'Research Lab'),
]


def seed_attributes(apps, schema_editor):
    Attribute       = apps.get_model('core', 'Attribute')
    AttributeOption = apps.get_model('core', 'AttributeOption')

    se_attr, _ = Attribute.objects.get_or_create(
        slug='stock-exchange',
        defaults={'name': 'Stock Exchange'},
    )
    for slug, name in STOCK_EXCHANGES:
        AttributeOption.objects.get_or_create(
            attribute=se_attr, slug=slug,
            defaults={'name': name},
        )

    ot_attr, _ = Attribute.objects.get_or_create(
        slug='org-type',
        defaults={'name': 'Organization Type'},
    )
    for slug, name in ORG_TYPES:
        AttributeOption.objects.get_or_create(
            attribute=ot_attr, slug=slug,
            defaults={'name': name},
        )


def unseed_attributes(apps, schema_editor):
    Attribute = apps.get_model('core', 'Attribute')
    Attribute.objects.filter(slug__in=['stock-exchange', 'org-type']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0075_organization_fields'),
    ]

    operations = [
        migrations.RunPython(seed_attributes, unseed_attributes),
    ]
