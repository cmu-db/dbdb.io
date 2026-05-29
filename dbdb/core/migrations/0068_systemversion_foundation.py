from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0067_flatpagemeta_modified'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemversion',
            name='governance',
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={'attribute__slug': 'governance'},
                related_name='system_governance',
                to='core.attributeoption',
                verbose_name='Governance',
            ),
        ),
    ]
