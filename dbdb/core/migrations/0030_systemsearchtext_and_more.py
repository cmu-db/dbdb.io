# Generated by Django 4.1.3 on 2023-07-03 19:50

import dbdb.core.common.searchvector
import django.contrib.postgres.indexes
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_postgresql_search_extensions'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSearchText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('search_text', models.TextField(default=None, help_text='Synthesized text for searching', null=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('system', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='search', to='core.system')),
            ],
            options={
                'verbose_name': 'System Search Text',
            },
        ),
        migrations.AddIndex(
            model_name='systemsearchtext',
            index=django.contrib.postgres.indexes.GinIndex(dbdb.core.common.searchvector.SearchVector('search_text', config='simple'), fastupdate=False, name='core_system_search__cf51c1_gin'),
        ),
    ]
