# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'System.description_sql_markup_type'
        db.add_column(u'systems_system', 'description_sql_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_sql_rendered'
        db.add_column(u'systems_system', '_description_sql_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_foreignkeys_markup_type'
        db.add_column(u'systems_system', 'description_foreignkeys_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_foreignkeys_rendered'
        db.add_column(u'systems_system', '_description_foreignkeys_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_serverside_markup_type'
        db.add_column(u'systems_system', 'description_serverside_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_serverside_rendered'
        db.add_column(u'systems_system', '_description_serverside_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_mapreduce_markup_type'
        db.add_column(u'systems_system', 'description_mapreduce_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_mapreduce_rendered'
        db.add_column(u'systems_system', '_description_mapreduce_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_secondary_markup_type'
        db.add_column(u'systems_system', 'description_secondary_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_secondary_rendered'
        db.add_column(u'systems_system', '_description_secondary_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_durability_markup_type'
        db.add_column(u'systems_system', 'description_durability_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_durability_rendered'
        db.add_column(u'systems_system', '_description_durability_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_triggers_markup_type'
        db.add_column(u'systems_system', 'description_triggers_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_triggers_rendered'
        db.add_column(u'systems_system', '_description_triggers_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_concurrency_markup_type'
        db.add_column(u'systems_system', 'description_concurrency_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_concurrency_rendered'
        db.add_column(u'systems_system', '_description_concurrency_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_datascheme_markup_type'
        db.add_column(u'systems_system', 'description_datascheme_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_datascheme_rendered'
        db.add_column(u'systems_system', '_description_datascheme_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_xml_markup_type'
        db.add_column(u'systems_system', 'description_xml_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_xml_rendered'
        db.add_column(u'systems_system', '_description_xml_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_typing_markup_type'
        db.add_column(u'systems_system', 'description_typing_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_typing_rendered'
        db.add_column(u'systems_system', '_description_typing_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_userconcepts_markup_type'
        db.add_column(u'systems_system', 'description_userconcepts_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_userconcepts_rendered'
        db.add_column(u'systems_system', '_description_userconcepts_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_transactionconcepts_markup_type'
        db.add_column(u'systems_system', 'description_transactionconcepts_markup_type',
                      self.gf('django.db.models.fields.CharField')(default='markdown', max_length=30),
                      keep_default=False)

        # Adding field 'System._description_transactionconcepts_rendered'
        db.add_column(u'systems_system', '_description_transactionconcepts_rendered',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)


        # Changing field 'System.description_transactionconcepts'
        db.alter_column(u'systems_system', 'description_transactionconcepts', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_typing'
        db.alter_column(u'systems_system', 'description_typing', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_datascheme'
        db.alter_column(u'systems_system', 'description_datascheme', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_concurrency'
        db.alter_column(u'systems_system', 'description_concurrency', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_triggers'
        db.alter_column(u'systems_system', 'description_triggers', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_mapreduce'
        db.alter_column(u'systems_system', 'description_mapreduce', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_durability'
        db.alter_column(u'systems_system', 'description_durability', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_userconcepts'
        db.alter_column(u'systems_system', 'description_userconcepts', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_secondary'
        db.alter_column(u'systems_system', 'description_secondary', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_serverside'
        db.alter_column(u'systems_system', 'description_serverside', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_foreignkeys'
        db.alter_column(u'systems_system', 'description_foreignkeys', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_xml'
        db.alter_column(u'systems_system', 'description_xml', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

        # Changing field 'System.description_sql'
        db.alter_column(u'systems_system', 'description_sql', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

    def backwards(self, orm):
        # Deleting field 'System.description_sql_markup_type'
        db.delete_column(u'systems_system', 'description_sql_markup_type')

        # Deleting field 'System._description_sql_rendered'
        db.delete_column(u'systems_system', '_description_sql_rendered')

        # Deleting field 'System.description_foreignkeys_markup_type'
        db.delete_column(u'systems_system', 'description_foreignkeys_markup_type')

        # Deleting field 'System._description_foreignkeys_rendered'
        db.delete_column(u'systems_system', '_description_foreignkeys_rendered')

        # Deleting field 'System.description_serverside_markup_type'
        db.delete_column(u'systems_system', 'description_serverside_markup_type')

        # Deleting field 'System._description_serverside_rendered'
        db.delete_column(u'systems_system', '_description_serverside_rendered')

        # Deleting field 'System.description_mapreduce_markup_type'
        db.delete_column(u'systems_system', 'description_mapreduce_markup_type')

        # Deleting field 'System._description_mapreduce_rendered'
        db.delete_column(u'systems_system', '_description_mapreduce_rendered')

        # Deleting field 'System.description_secondary_markup_type'
        db.delete_column(u'systems_system', 'description_secondary_markup_type')

        # Deleting field 'System._description_secondary_rendered'
        db.delete_column(u'systems_system', '_description_secondary_rendered')

        # Deleting field 'System.description_durability_markup_type'
        db.delete_column(u'systems_system', 'description_durability_markup_type')

        # Deleting field 'System._description_durability_rendered'
        db.delete_column(u'systems_system', '_description_durability_rendered')

        # Deleting field 'System.description_triggers_markup_type'
        db.delete_column(u'systems_system', 'description_triggers_markup_type')

        # Deleting field 'System._description_triggers_rendered'
        db.delete_column(u'systems_system', '_description_triggers_rendered')

        # Deleting field 'System.description_concurrency_markup_type'
        db.delete_column(u'systems_system', 'description_concurrency_markup_type')

        # Deleting field 'System._description_concurrency_rendered'
        db.delete_column(u'systems_system', '_description_concurrency_rendered')

        # Deleting field 'System.description_datascheme_markup_type'
        db.delete_column(u'systems_system', 'description_datascheme_markup_type')

        # Deleting field 'System._description_datascheme_rendered'
        db.delete_column(u'systems_system', '_description_datascheme_rendered')

        # Deleting field 'System.description_xml_markup_type'
        db.delete_column(u'systems_system', 'description_xml_markup_type')

        # Deleting field 'System._description_xml_rendered'
        db.delete_column(u'systems_system', '_description_xml_rendered')

        # Deleting field 'System.description_typing_markup_type'
        db.delete_column(u'systems_system', 'description_typing_markup_type')

        # Deleting field 'System._description_typing_rendered'
        db.delete_column(u'systems_system', '_description_typing_rendered')

        # Deleting field 'System.description_userconcepts_markup_type'
        db.delete_column(u'systems_system', 'description_userconcepts_markup_type')

        # Deleting field 'System._description_userconcepts_rendered'
        db.delete_column(u'systems_system', '_description_userconcepts_rendered')

        # Deleting field 'System.description_transactionconcepts_markup_type'
        db.delete_column(u'systems_system', 'description_transactionconcepts_markup_type')

        # Deleting field 'System._description_transactionconcepts_rendered'
        db.delete_column(u'systems_system', '_description_transactionconcepts_rendered')


        # Changing field 'System.description_transactionconcepts'
        db.alter_column(u'systems_system', 'description_transactionconcepts', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_typing'
        db.alter_column(u'systems_system', 'description_typing', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_datascheme'
        db.alter_column(u'systems_system', 'description_datascheme', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_concurrency'
        db.alter_column(u'systems_system', 'description_concurrency', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_triggers'
        db.alter_column(u'systems_system', 'description_triggers', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_mapreduce'
        db.alter_column(u'systems_system', 'description_mapreduce', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_durability'
        db.alter_column(u'systems_system', 'description_durability', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_userconcepts'
        db.alter_column(u'systems_system', 'description_userconcepts', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_secondary'
        db.alter_column(u'systems_system', 'description_secondary', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_serverside'
        db.alter_column(u'systems_system', 'description_serverside', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_foreignkeys'
        db.alter_column(u'systems_system', 'description_foreignkeys', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_xml'
        db.alter_column(u'systems_system', 'description_xml', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_sql'
        db.alter_column(u'systems_system', 'description_sql', self.gf('django.db.models.fields.TextField')(null=True))

    models = {
        u'systems.apiaccessmethods': {
            'Meta': {'object_name': 'APIAccessMethods'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'website': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True'})
        },
        u'systems.dbmodel': {
            'Meta': {'object_name': 'DBModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'website': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True'})
        },
        u'systems.license': {
            'Meta': {'object_name': 'License'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'website': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True'})
        },
        u'systems.operatingsystem': {
            'Meta': {'object_name': 'OperatingSystem'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'null': 'True'})
        },
        u'systems.programminglanguage': {
            'Meta': {'object_name': 'ProgrammingLanguage'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'null': 'True'})
        },
        u'systems.publication': {
            'Meta': {'object_name': 'Publication'},
            'authors': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'bibtex': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'download': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {})
        },
        u'systems.system': {
            'Meta': {'object_name': 'System'},
            '_description_concurrency_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_datascheme_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_durability_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_foreignkeys_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_mapreduce_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_secondary_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_serverside_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_sql_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_transactionconcepts_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_triggers_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_typing_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_userconcepts_rendered': ('django.db.models.fields.TextField', [], {}),
            '_description_xml_rendered': ('django.db.models.fields.TextField', [], {}),
            'access_methods': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems'", 'symmetrical': 'False', 'to': u"orm['systems.APIAccessMethods']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'dbmodel': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems'", 'symmetrical': 'False', 'to': u"orm['systems.DBModel']"}),
            'default_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'derived_from': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'derived_from_rel_+'", 'to': u"orm['systems.System']"}),
            'description': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_concurrency': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_concurrency_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_datascheme': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_datascheme_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_durability': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_durability_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_foreignkeys': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_foreignkeys_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_mapreduce': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_mapreduce_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_secondary': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_secondary_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_serverside': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_serverside_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_sql': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_sql_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_transactionconcepts': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_transactionconcepts_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_triggers': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_triggers_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_typing': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_typing_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_userconcepts': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_userconcepts_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'description_xml': ('markupfield.fields.MarkupField', [], {'default': 'None', 'null': 'True', 'rendered_field': 'True'}),
            'description_xml_markup_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '30'}),
            'developer': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64', 'null': 'True'}),
            'end_year': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'license': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems'", 'symmetrical': 'False', 'to': u"orm['systems.License']"}),
            'logo_img': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True'}),
            'max_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'oses': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems'", 'symmetrical': 'False', 'to': u"orm['systems.OperatingSystem']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1', 'null': 'True'}),
            'publications': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems'", 'symmetrical': 'False', 'to': u"orm['systems.Publication']"}),
            'secret_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100'}),
            'start_year': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'support_concurrency': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_datascheme': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_durability': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_foreignkeys': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_languages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems_supported'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"}),
            'support_mapreduce': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_secondary': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_serverside': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_sql': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_transactionconcepts': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_triggers': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_typing': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_userconcepts': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_xml': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'tech_docs': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'null': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'null': 'True'}),
            'written_in': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems_written'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"})
        }
    }

    complete_apps = ['systems']