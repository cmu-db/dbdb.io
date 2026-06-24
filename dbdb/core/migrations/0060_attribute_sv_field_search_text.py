from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_add_attribute_attributeoption'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='sv_field',
            field=models.CharField(
                blank=True, max_length=64, verbose_name='SystemVersion field',
                help_text="Name of the SystemVersion M2M field (e.g. 'attr_tags'). "
                          "Used to build browse filters automatically."),
        ),
        migrations.AddField(
            model_name='attribute',
            name='search_text',
            field=models.CharField(
                blank=True, max_length=200,
                help_text="Browse search description format string. Use {names} for the joined option names "
                          "(e.g. ' Tagged with {names}')."),
        ),
    ]