import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0064_add_logo_fields_to_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='feature',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='feature',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
