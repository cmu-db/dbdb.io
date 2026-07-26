import django.db.models.deletion
from django.db import migrations, models


# Integer values from the old StockExchange.IntegerChoices → AttributeOption slug
_INT_TO_SLUG = {
    1: 'nyse',
    2: 'nasdaq',
    3: 'lse',
    4: 'tse',
    5: 'hkex',
    6: 'asx',
    7: 'tsx',
    8: 'euronext',
    9: 'other',
}

# Seed data: (slug, name, url) — mirrors the old StockExchange.url dict
_STOCK_EXCHANGES = [
    ('nyse',     'NYSE',     'https://www.nyse.com/quote/XNYS:'),
    ('nasdaq',   'NASDAQ',   'https://www.nasdaq.com/market-activity/stocks/'),
    ('lse',      'LSE',      'https://www.londonstockexchange.com'),
    ('tse',      'TSE',      'https://www.jpx.co.jp/english/'),
    ('hkex',     'HKEX',     'https://www.hkex.com.hk'),
    ('asx',      'ASX',      'https://www.asx.com.au'),
    ('tsx',      'TSX',      'https://www.tsx.com'),
    ('euronext', 'Euronext', 'https://www.euronext.com'),
    ('other',    'Other',    ''),
]


def migrate_to_fk(apps, schema_editor):
    Attribute       = apps.get_model('core', 'Attribute')
    AttributeOption = apps.get_model('core', 'AttributeOption')
    Organization    = apps.get_model('core', 'Organization')

    se_attr, _ = Attribute.objects.get_or_create(
        slug='stock-exchange',
        defaults={'name': 'Stock Exchange'},
    )
    slug_to_option = {}
    for slug, name, url in _STOCK_EXCHANGES:
        opt, _ = AttributeOption.objects.update_or_create(
            attribute=se_attr, slug=slug,
            defaults={'name': name, 'url': url},
        )
        slug_to_option[slug] = opt

    for org in Organization.objects.filter(stock_exchange_int__isnull=False):
        slug = _INT_TO_SLUG.get(org.stock_exchange_int)
        if slug:
            org.stock_exchange = slug_to_option[slug]
            org.save(update_fields=['stock_exchange'])


def reverse_to_int(apps, schema_editor):
    _SLUG_TO_INT = {v: k for k, v in _INT_TO_SLUG.items()}
    Organization = apps.get_model('core', 'Organization')
    for org in Organization.objects.filter(stock_exchange__isnull=False):
        slug = org.stock_exchange.slug
        int_val = _SLUG_TO_INT.get(slug)
        if int_val is not None:
            org.stock_exchange_int = int_val
            org.save(update_fields=['stock_exchange_int'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0098_unique_user_email'),
    ]

    operations = [
        # 1. Preserve old integer data under a temporary name
        migrations.RenameField(
            model_name='organization',
            old_name='stock_exchange',
            new_name='stock_exchange_int',
        ),
        # 2. Add the new FK column (nullable)
        migrations.AddField(
            model_name='organization',
            name='stock_exchange',
            field=models.ForeignKey(
                blank=True, null=True,
                limit_choices_to={'attribute__slug': 'stock-exchange'},
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='org_stock_exchanges',
                to='core.attributeoption',
                verbose_name='Stock Exchange',
            ),
        ),
        # 3. Populate FK from old integer values
        migrations.RunPython(migrate_to_fk, reverse_to_int),
        # 4. Drop the old integer column
        migrations.RemoveField(
            model_name='organization',
            name='stock_exchange_int',
        ),
    ]
