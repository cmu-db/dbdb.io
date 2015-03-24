# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'System.description_markup_type'
        db.delete_column(u'systems_system', 'description_markup_type')

        # Deleting field 'System._description_rendered'
        db.delete_column(u'systems_system', '_description_rendered')


        # Changing field 'System.description'
        db.alter_column(u'systems_system', 'description', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'System.description_markup_type'
        raise RuntimeError("Cannot reverse this migration. 'System.description_markup_type' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'System.description_markup_type'
        db.add_column(u'systems_system', 'description_markup_type',
                      self.gf('django.db.models.fields.CharField')(default=None, max_length=30),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'System._description_rendered'
        raise RuntimeError("Cannot reverse this migration. 'System._description_rendered' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'System._description_rendered'
        db.add_column(u'systems_system', '_description_rendered',
                      self.gf('django.db.models.fields.TextField')(),
                      keep_default=False)


        # Changing field 'System.description'
        db.alter_column(u'systems_system', 'description', self.gf('markupfield.fields.MarkupField')(null=True, rendered_field=True))

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
            'access_methods': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems'", 'symmetrical': 'False', 'to': u"orm['systems.APIAccessMethods']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'dbmodel': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'systems'", 'symmetrical': 'False', 'to': u"orm['systems.DBModel']"}),
            'default_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'derived_from': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'derived_from_rel_+'", 'to': u"orm['systems.System']"}),
            'description': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True'}),
            'description_concurrency': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_datascheme': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_durability': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_foreignkeys': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_mapreduce': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_secondary': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_serverside': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_sql': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_transactionconcepts': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_triggers': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_typing': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_userconcepts': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_xml': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
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