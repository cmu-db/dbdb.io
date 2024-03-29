# Generated by Django 4.1.3 on 2022-12-03 03:12

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_feature_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemversion',
            name='countries',
            field=django_countries.fields.CountryField(blank=True, help_text='Country of where the DBMS company or project started', max_length=747, multiple=True, verbose_name='Countries of Origin'),
        ),
    ]
