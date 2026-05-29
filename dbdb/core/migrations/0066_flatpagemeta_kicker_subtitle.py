from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0065_add_timestamps_to_feature'),
    ]

    operations = [
        migrations.AddField(
            model_name='flatpagemeta',
            name='kicker',
            field=models.CharField(
                blank=True,
                max_length=100,
                help_text="Short label shown above the page title (e.g. 'About', 'Resources').",
            ),
        ),
        migrations.AddField(
            model_name='flatpagemeta',
            name='subtitle',
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text="Italic subheading shown below the page title.",
            ),
        ),
    ]
