import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0077_organization_choices'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SuggestedSystem',
            new_name='SystemSuggestion',
        ),
        migrations.RenameField(
            model_name='systemsuggestion',
            old_name='url',
            new_name='system_url',
        ),
        migrations.RemoveField(
            model_name='systemsuggestion',
            name='description',
        ),
        migrations.RemoveField(
            model_name='systemsuggestion',
            name='approved',
        ),
        migrations.RemoveField(
            model_name='systemsuggestion',
            name='secret_key',
        ),
        migrations.AlterField(
            model_name='systemsuggestion',
            name='email',
            field=models.EmailField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='systemsuggestion',
            name='system_url',
            field=models.URLField(max_length=500),
        ),
        migrations.AddField(
            model_name='systemsuggestion',
            name='sourcerepo_url',
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='systemsuggestion',
            name='logo_url',
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='systemsuggestion',
            name='is_my_system',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='systemsuggestion',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='systemsuggestion',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='systemsuggestion',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='systemsuggestion',
            name='system',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='suggestions',
                to='core.system',
            ),
        ),
        migrations.AlterModelOptions(
            name='systemsuggestion',
            options={'ordering': ('-created',)},
        ),
    ]
