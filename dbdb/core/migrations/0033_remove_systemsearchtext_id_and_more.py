# Generated by Django 4.1.10 on 2023-10-25 01:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_systemsearchtext_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='systemsearchtext',
            name='id',
        ),
        migrations.AlterField(
            model_name='systemsearchtext',
            name='system',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='core.system'),
        ),
    ]