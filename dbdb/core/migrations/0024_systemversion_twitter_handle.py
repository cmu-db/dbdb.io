# Generated by Django 3.1.14 on 2022-01-02 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_auto_20220102_1437'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemversion',
            name='twitter_handle',
            field=models.CharField(blank=True, help_text='Twitter account for the database (avoid company account if possible)', max_length=100),
        ),
    ]