import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0066_flatpagemeta_kicker_subtitle'),
    ]

    operations = [
        migrations.AddField(
            model_name='flatpagemeta',
            name='modified',
            field=models.DateTimeField(
                auto_now=True,
                help_text="Automatically updated whenever this record is saved.",
            ),
        ),
    ]
