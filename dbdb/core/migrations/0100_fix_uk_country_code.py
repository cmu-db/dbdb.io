from django.db import migrations

# Non-ISO country codes that were imported as-is → their ISO 3166-1 alpha-2 code
_FIXES = {'UK': 'GB'}


def fix_country_codes(apps, schema_editor):
    for model_name in ('SystemVersion', 'Organization'):
        model = apps.get_model('core', model_name)
        for obj_id, raw in model.objects.exclude(countries='').values_list('id', 'countries'):
            codes = [c for c in str(raw).split(',') if c]
            fixed = list(dict.fromkeys(_FIXES.get(c, c) for c in codes))
            if fixed != codes:
                model.objects.filter(id=obj_id).update(countries=','.join(fixed))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0099_organization_stock_exchange_fk'),
    ]

    operations = [
        migrations.RunPython(fix_country_codes, migrations.RunPython.noop),
    ]
