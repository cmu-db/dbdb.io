# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'OperatingSystem'
        db.create_table(u'systems_operatingsystem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('website', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True)),
        ))
        db.send_create_signal(u'systems', ['OperatingSystem'])

        # Adding model 'ProgrammingLanguage'
        db.create_table(u'systems_programminglanguage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('website', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True)),
        ))
        db.send_create_signal(u'systems', ['ProgrammingLanguage'])

        # Adding model 'License'
        db.create_table(u'systems_license', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('website', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True)),
        ))
        db.send_create_signal(u'systems', ['License'])

        # Adding model 'ConcurrencyControl'
        db.create_table(u'systems_concurrencycontrol', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'systems', ['ConcurrencyControl'])

        # Adding model 'Publication'
        db.create_table(u'systems_publication', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('authors', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('bibtex', self.gf('django.db.models.fields.TextField')(default=None, null=True, blank=True)),
            ('download', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True, blank=True)),
            ('year', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'systems', ['Publication'])

        # Adding model 'System'
        db.create_table(u'systems_system', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('description', self.gf('django.db.models.fields.TextField')(default=None)),
            ('website', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True)),
            ('developer', self.gf('django.db.models.fields.CharField')(default=None, max_length=64, null=True)),
            ('project_type', self.gf('django.db.models.fields.CharField')(default=None, max_length=1, null=True)),
            ('start_year', self.gf('django.db.models.fields.IntegerField')(default=None, null=True)),
            ('end_year', self.gf('django.db.models.fields.IntegerField')(default=None, null=True)),
            ('support_sql', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('support_foreignkeys', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('support_serverside', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('support_mapreduce', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('support_secondary', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('support_durability', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('support_triggers', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('default_isolation', self.gf('django.db.models.fields.CharField')(default=None, max_length=2, null=True)),
            ('max_isolation', self.gf('django.db.models.fields.CharField')(default=None, max_length=2, null=True)),
            ('concurrency', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['systems.ConcurrencyControl'])),
            ('secret_key', self.gf('django.db.models.fields.CharField')(default=None, max_length=100)),
        ))
        db.send_create_signal(u'systems', ['System'])

        # Adding M2M table for field written_in on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_written_in')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('programminglanguage', models.ForeignKey(orm[u'systems.programminglanguage'], null=False))
        ))
        db.create_unique(m2m_table_name, ['system_id', 'programminglanguage_id'])

        # Adding M2M table for field oses on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_oses')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('operatingsystem', models.ForeignKey(orm[u'systems.operatingsystem'], null=False))
        ))
        db.create_unique(m2m_table_name, ['system_id', 'operatingsystem_id'])

        # Adding M2M table for field publications on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_publications')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('publication', models.ForeignKey(orm[u'systems.publication'], null=False))
        ))
        db.create_unique(m2m_table_name, ['system_id', 'publication_id'])

        # Adding M2M table for field derived_from on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_derived_from')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('to_system', models.ForeignKey(orm[u'systems.system'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_system_id', 'to_system_id'])

        # Adding M2M table for field support_languages on 'System'
        m2m_table_name = db.shorten_name(u'systems_system_support_languages')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('system', models.ForeignKey(orm[u'systems.system'], null=False)),
            ('programminglanguage', models.ForeignKey(orm[u'systems.programminglanguage'], null=False))
        ))
        db.create_unique(m2m_table_name, ['system_id', 'programminglanguage_id'])


    def backwards(self, orm):
        # Deleting model 'OperatingSystem'
        db.delete_table(u'systems_operatingsystem')

        # Deleting model 'ProgrammingLanguage'
        db.delete_table(u'systems_programminglanguage')

        # Deleting model 'License'
        db.delete_table(u'systems_license')

        # Deleting model 'ConcurrencyControl'
        db.delete_table(u'systems_concurrencycontrol')

        # Deleting model 'Publication'
        db.delete_table(u'systems_publication')

        # Deleting model 'System'
        db.delete_table(u'systems_system')

        # Removing M2M table for field written_in on 'System'
        db.delete_table(db.shorten_name(u'systems_system_written_in'))

        # Removing M2M table for field oses on 'System'
        db.delete_table(db.shorten_name(u'systems_system_oses'))

        # Removing M2M table for field publications on 'System'
        db.delete_table(db.shorten_name(u'systems_system_publications'))

        # Removing M2M table for field derived_from on 'System'
        db.delete_table(db.shorten_name(u'systems_system_derived_from'))

        # Removing M2M table for field support_languages on 'System'
        db.delete_table(db.shorten_name(u'systems_system_support_languages'))


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