# Generated by Django 4.1.3 on 2023-07-10 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_rename_system_systemfeature_version_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsearchtext',
            name='name',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
    ]