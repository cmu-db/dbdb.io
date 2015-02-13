# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DBModel'
        db.create_table(u'systems_dbmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('website', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True)),
        ))
        db.send_create_signal(u'systems', ['DBModel'])

        # Adding model 'APIAccessMethods'
        db.create_table(u'systems_apiaccessmethods', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('website', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True)),
        ))
        db.send_create_signal(u'systems', ['APIAccessMethods'])

        # Adding field 'System.tech_docs'
        db.add_column(u'systems_system', 'tech_docs',
                      self.gf('django.db.models.fields.URLField')(default='', max_length=200, null=True),
                      keep_default=False)

        # Adding field 'System.logo_img'
        db.add_column(u'systems_system', 'logo_img',
                      self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True),
                      keep_default=False)

        # Adding field 'System.support_datascheme'
        db.add_column(u'systems_system', 'support_datascheme',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.description_datascheme'
        db.add_column(u'systems_system', 'description_datascheme',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.support_xml'
        db.add_column(u'systems_system', 'support_xml',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.description_xml'
        db.add_column(u'systems_system', 'description_xml',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.support_typing'
        db.add_column(u'systems_system', 'support_typing',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.description_typing'
        db.add_column(u'systems_system', 'description_typing',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.support_userconcepts'
        db.add_column(u'systems_system', 'support_userconcepts',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.description_userconcepts'
        db.add_column(u'systems_system', 'description_userconcepts',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.support_transactionconcepts'
        db.add_column(u'systems_system', 'support_transactionconcepts',
                      self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.description_transactionconcepts'
        db.add_column(u'systems_system', 'description_transactionconcepts',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.created'
        db.add_column(u'systems_system', 'created',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True),
                      keep_default=False)

        # Adding field 'System.updated'
        db.add_column(u'systems_system', 'updated',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, null=True, blank=True),
                      keep_default=False)

        # Adding M2M table for field dbmodel on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_dbmodel')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('dbmodel', models.ForeignKey(orm[u'systems.dbmodel'], null=False))
        ))
        db.create_unique(m2m_table_name, ['system_id', 'dbmodel_id'])

        # Adding M2M table for field license on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_license')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('license', models.ForeignKey(orm[u'systems.license'], null=False))
        ))
        db.create_unique(m2m_table_name, ['system_id', 'license_id'])

        # Adding M2M table for field access_methods on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_access_methods')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('apiaccessmethods', models.ForeignKey(orm[u'systems.apiaccessmethods'], null=False))
        ))
        db.create_unique(m2m_table_name, ['system_id', 'apiaccessmethods_id'])


        # Changing field 'System.support_sql'
        db.alter_column(u'systems_system', 'support_sql', self.gf('django.db.models.fields.NullBooleanField')(null=True))

        # Changing field 'System.description_concurrency'
        db.alter_column(u'systems_system', 'description_concurrency', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_triggers'
        db.alter_column(u'systems_system', 'description_triggers', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.support_durability'
        db.alter_column(u'systems_system', 'support_durability', self.gf('django.db.models.fields.NullBooleanField')(null=True))

        # Changing field 'System.description_mapreduce'
        db.alter_column(u'systems_system', 'description_mapreduce', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_durability'
        db.alter_column(u'systems_system', 'description_durability', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_secondary'
        db.alter_column(u'systems_system', 'description_secondary', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.description_serverside'
        db.alter_column(u'systems_system', 'description_serverside', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.support_concurrency'
        db.alter_column(u'systems_system', 'support_concurrency', self.gf('django.db.models.fields.NullBooleanField')(null=True))

        # Changing field 'System.support_serverside'
        db.alter_column(u'systems_system', 'support_serverside', self.gf('django.db.models.fields.NullBooleanField')(null=True))

        # Changing field 'System.support_secondary'
        db.alter_column(u'systems_system', 'support_secondary', self.gf('django.db.models.fields.NullBooleanField')(null=True))

        # Changing field 'System.description_foreignkeys'
        db.alter_column(u'systems_system', 'description_foreignkeys', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.support_triggers'
        db.alter_column(u'systems_system', 'support_triggers', self.gf('django.db.models.fields.NullBooleanField')(null=True))

        # Changing field 'System.support_mapreduce'
        db.alter_column(u'systems_system', 'support_mapreduce', self.gf('django.db.models.fields.NullBooleanField')(null=True))

        # Changing field 'System.description_sql'
        db.alter_column(u'systems_system', 'description_sql', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'System.support_foreignkeys'
        db.alter_column(u'systems_system', 'support_foreignkeys', self.gf('django.db.models.fields.NullBooleanField')(null=True))

    def backwards(self, orm):
        # Deleting model 'DBModel'
        db.delete_table(u'systems_dbmodel')

        # Deleting model 'APIAccessMethods'
        db.delete_table(u'systems_apiaccessmethods')

        # Deleting field 'System.tech_docs'
        db.delete_column(u'systems_system', 'tech_docs')

        # Deleting field 'System.logo_img'
        db.delete_column(u'systems_system', 'logo_img')

        # Deleting field 'System.support_datascheme'
        db.delete_column(u'systems_system', 'support_datascheme')

        # Deleting field 'System.description_datascheme'
        db.delete_column(u'systems_system', 'description_datascheme')

        # Deleting field 'System.support_xml'
        db.delete_column(u'systems_system', 'support_xml')

        # Deleting field 'System.description_xml'
        db.delete_column(u'systems_system', 'description_xml')

        # Deleting field 'System.support_typing'
        db.delete_column(u'systems_system', 'support_typing')

        # Deleting field 'System.description_typing'
        db.delete_column(u'systems_system', 'description_typing')

        # Deleting field 'System.support_userconcepts'
        db.delete_column(u'systems_system', 'support_userconcepts')

        # Deleting field 'System.description_userconcepts'
        db.delete_column(u'systems_system', 'description_userconcepts')

        # Deleting field 'System.support_transactionconcepts'
        db.delete_column(u'systems_system', 'support_transactionconcepts')

        # Deleting field 'System.description_transactionconcepts'
        db.delete_column(u'systems_system', 'description_transactionconcepts')

        # Deleting field 'System.created'
        db.delete_column(u'systems_system', 'created')

        # Deleting field 'System.updated'
        db.delete_column(u'systems_system', 'updated')

        # Removing M2M table for field dbmodel on 'System'
        db.delete_table(db.shorten_name(u'systems_system_dbmodel'))

        # Removing M2M table for field license on 'System'
        db.delete_table(db.shorten_name(u'systems_system_license'))

        # Removing M2M table for field access_methods on 'System'
        db.delete_table(db.shorten_name(u'systems_system_access_methods'))


        # Changing field 'System.support_sql'
        db.alter_column(u'systems_system', 'support_sql', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'System.description_concurrency'
        db.alter_column(u'systems_system', 'description_concurrency', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.description_triggers'
        db.alter_column(u'systems_system', 'description_triggers', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.support_durability'
        db.alter_column(u'systems_system', 'support_durability', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'System.description_mapreduce'
        db.alter_column(u'systems_system', 'description_mapreduce', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.description_durability'
        db.alter_column(u'systems_system', 'description_durability', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.description_secondary'
        db.alter_column(u'systems_system', 'description_secondary', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.description_serverside'
        db.alter_column(u'systems_system', 'description_serverside', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.support_concurrency'
        db.alter_column(u'systems_system', 'support_concurrency', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'System.support_serverside'
        db.alter_column(u'systems_system', 'support_serverside', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'System.support_secondary'
        db.alter_column(u'systems_system', 'support_secondary', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'System.description_foreignkeys'
        db.alter_column(u'systems_system', 'description_foreignkeys', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.support_triggers'
        db.alter_column(u'systems_system', 'support_triggers', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'System.support_mapreduce'
        db.alter_column(u'systems_system', 'support_mapreduce', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'System.description_sql'
        db.alter_column(u'systems_system', 'description_sql', self.gf('django.db.models.fields.TextField')())

        # Changing field 'System.support_foreignkeys'
        db.alter_column(u'systems_system', 'support_foreignkeys', self.gf('django.db.models.fields.BooleanField')())

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
            'access_methods': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'dbs'", 'symmetrical': 'False', 'to': u"orm['systems.APIAccessMethods']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'dbmodel': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'dbs'", 'symmetrical': 'False', 'to': u"orm['systems.DBModel']"}),
            'default_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'derived_from': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'derived_from_rel_+'", 'to': u"orm['systems.System']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''"}),
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
            'license': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'dbs'", 'symmetrical': 'False', 'to': u"orm['systems.License']"}),
            'logo_img': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True'}),
            'max_isolation': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '2', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'oses': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'os+'", 'symmetrical': 'False', 'to': u"orm['systems.OperatingSystem']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1', 'null': 'True'}),
            'publications': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'p+'", 'symmetrical': 'False', 'to': u"orm['systems.Publication']"}),
            'secret_key': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '100'}),
            'start_year': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'support_concurrency': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_datascheme': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_durability': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_foreignkeys': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'support_languages': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'+l'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"}),
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
            'written_in': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'wi+'", 'symmetrical': 'False', 'to': u"orm['systems.ProgrammingLanguage']"})
        }
    }

    complete_apps = ['systems']