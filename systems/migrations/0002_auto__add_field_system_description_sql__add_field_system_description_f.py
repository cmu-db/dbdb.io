# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'System.description_sql'
        db.add_column(u'systems_system', 'description_sql',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_foreignkeys'
        db.add_column(u'systems_system', 'description_foreignkeys',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_serverside'
        db.add_column(u'systems_system', 'description_serverside',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_mapreduce'
        db.add_column(u'systems_system', 'description_mapreduce',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_secondary'
        db.add_column(u'systems_system', 'description_secondary',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_durability'
        db.add_column(u'systems_system', 'description_durability',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)

        # Adding field 'System.description_triggers'
        db.add_column(u'systems_system', 'description_triggers',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'System.description_sql'
        db.delete_column(u'systems_system', 'description_sql')

        # Deleting field 'System.description_foreignkeys'
        db.delete_column(u'systems_system', 'description_foreignkeys')

        # Deleting field 'System.description_serverside'
        db.delete_column(u'systems_system', 'description_serverside')

        # Deleting field 'System.description_mapreduce'
        db.delete_column(u'systems_system', 'description_mapreduce')

        # Deleting field 'System.description_secondary'
        db.delete_column(u'systems_system', 'description_secondary')

        # Deleting field 'System.description_durability'
        db.delete_column(u'systems_system', 'description_durability')

        # Deleting field 'System.description_triggers'
        db.delete_column(u'systems_system', 'description_triggers')


    models = {
        u'systems.concurrencycontrol': {
            'Meta': {'object_name': 'ConcurrencyControl'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '16'})
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
            'website': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True'})
        },
        u'systems.programminglanguage': {
            'Meta': {'object_name': 'ProgrammingLanguage'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'website': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True'})
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
            'concurrency': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['systems.ConcurrencyControl']"}),
            'default_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'derived_from': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'derived_from_rel_+'", 'to': u"orm['systems.System']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': 'None'}),
            'description_durability': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_foreignkeys': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_mapreduce': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_secondary': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_serverside': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_sql': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_triggers': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'developer': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True'}),
            'end_year': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'oses': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'os+'", 'symmetrical': 'False', 'to': u"orm['systems.OperatingSystem']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '1', 'null': 'True'}),
            'publications': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'p+'", 'symmetrical': 'False', 'to': u"orm['systems.Publication']"}),
            'secret_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100'}),
            'start_year': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True'}),
            'support_durability': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_foreignkeys': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_languages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'+l'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"}),
            'support_mapreduce': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_secondary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_serverside': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_sql': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_triggers': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'website': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True'}),
            'written_in': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'wi+'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"})
        }
    }

    complete_apps = ['systems']