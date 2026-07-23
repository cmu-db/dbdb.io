import uuid
from django.db import migrations


def fix_duplicate_emails(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    # Keep the oldest account's email intact; rename every newer duplicate so
    # an admin can find and fix them (look for email__startswith='FIXME-').
    seen = {}
    for user in User.objects.exclude(email='').order_by('date_joined'):
        key = user.email.lower()
        if key in seen:
            local, _, domain = user.email.partition('@')
            suffix = 'FIXME-' + uuid.uuid4().hex[:8]
            user.email = f'{local}-{suffix}@{domain}'
            user.save(update_fields=['email'])
        else:
            seen[key] = user.pk


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('core', '0097_systemversion_twitter_url'),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_emails, migrations.RunPython.noop),
        # Partial unique index: enforces uniqueness only on non-empty emails so
        # that multiple accounts with no email (email='') remain allowed.
        migrations.RunSQL(
            sql="CREATE UNIQUE INDEX auth_user_email_nonempty ON auth_user (email) WHERE email != ''",
            reverse_sql="DROP INDEX IF EXISTS auth_user_email_nonempty",
        ),
    ]
