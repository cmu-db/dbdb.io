# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'ConcurrencyControl'
        db.delete_table(u'systems_concurrencycontrol')

        # Deleting field 'System.concurrency'
        db.delete_column(u'systems_system', 'concurrency_id')

        # Adding field 'System.support_concurrency'
        db.add_column(u'systems_system', 'support_concurrency',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'System.description_concurrency'
        db.add_column(u'systems_system', 'description_concurrency',
                      self.gf('django.db.models.fields.TextField')(default=''),
                      keep_default=False)


    def backwards(self, orm):
        # Adding model 'ConcurrencyControl'
        db.create_table(u'systems_concurrencycontrol', (
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=16)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'systems', ['ConcurrencyControl'])


        # User chose to not deal with backwards NULL issues for 'System.concurrency'
        raise RuntimeError("Cannot reverse this migration. 'System.concurrency' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'System.concurrency'
        db.add_column(u'systems_system', 'concurrency',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['systems.ConcurrencyControl']),
                      keep_default=False)

        # Deleting field 'System.support_concurrency'
        db.delete_column(u'systems_system', 'support_concurrency')

        # Deleting field 'System.description_concurrency'
        db.delete_column(u'systems_system', 'description_concurrency')


    models = {
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
            'default_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'derived_from': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'derived_from_rel_+'", 'to': u"orm['systems.System']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_concurrency': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_durability': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_foreignkeys': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_mapreduce': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_secondary': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_serverside': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_sql': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'description_triggers': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'developer': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64', 'null': 'True'}),
            'end_year': ('django.db.models.fields.IntegerField', [], {'default': "''", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'oses': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'os+'", 'symmetrical': 'False', 'to': u"orm['systems.OperatingSystem']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1', 'null': 'True'}),
            'publications': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'p+'", 'symmetrical': 'False', 'to': u"orm['systems.Publication']"}),
            'secret_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100'}),
            'start_year': ('django.db.models.fields.IntegerField', [], {'default': "''", 'null': 'True'}),
            'support_concurrency': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_durability': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_foreignkeys': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_languages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'+l'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"}),
            'support_mapreduce': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_secondary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_serverside': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_sql': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'support_triggers': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'null': 'True'}),
            'written_in': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'wi+'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"})
        }
    }

    complete_apps = ['systems']