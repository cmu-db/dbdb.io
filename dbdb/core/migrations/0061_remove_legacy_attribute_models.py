"""
Phase 2 of the Attribute/AttributeOption consolidation.

Run manage.py copy_attributes BEFORE applying this migration.

This migration:
  1. Removes the old M2M fields on SystemVersion (tags→Tag, oses→OS, etc.)
  2. Renames the attr_* fields to their permanent names
  3. Drops the Tag, License, OperatingSystem, ProgrammingLanguage, and ProjectType tables
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_attribute_sv_field_search_text'),
    ]

    operations = [
        # Remove old M2M fields from SystemVersion
        migrations.RemoveField(model_name='systemversion', name='tags'),
        migrations.RemoveField(model_name='systemversion', name='project_types'),
        migrations.RemoveField(model_name='systemversion', name='licenses'),
        migrations.RemoveField(model_name='systemversion', name='oses'),
        migrations.RemoveField(model_name='systemversion', name='supported_languages'),
        migrations.RemoveField(model_name='systemversion', name='written_in'),

        # Rename attr_* fields to their permanent names
        migrations.RenameField(model_name='systemversion', old_name='attr_tags', new_name='tags'),
        migrations.RenameField(model_name='systemversion', old_name='attr_project_types', new_name='project_types'),
        migrations.RenameField(model_name='systemversion', old_name='attr_licenses', new_name='licenses'),
        migrations.RenameField(model_name='systemversion', old_name='attr_oses', new_name='oses'),
        migrations.RenameField(model_name='systemversion', old_name='attr_supported_languages', new_name='supported_languages'),
        migrations.RenameField(model_name='systemversion', old_name='attr_written_in', new_name='written_in'),

        # Drop legacy models
        migrations.DeleteModel(name='Tag'),
        migrations.DeleteModel(name='License'),
        migrations.DeleteModel(name='OperatingSystem'),
        migrations.DeleteModel(name='ProgrammingLanguage'),
        migrations.DeleteModel(name='ProjectType'),
    ]