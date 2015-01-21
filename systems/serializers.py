from rest_framework import serializers
from systems.models import System, OperatingSystem, ProgrammingLanguage

class SystemSerializer(serializers.ModelSerializer):
  class Meta:
  	model = System
  	fields = ('created', 'dbmodel', 'default_isolation',
      'derived_from', 'description', 'description_concurrency',
      'description_datascheme', 'description_durability',
      'description_foreignkeys', 'description_mapreduce',
      'description_secondary', 'description_serverside',
      'description_sql', 'description_transactionconcepts',
      'description_triggers', 'description_typing',
      'description_userconcepts', 'description_xml',
      'developer', 'end_year', 'id', 'license', 'logo_img',
      'max_isolation', 'name', 'oses', 'project_type',
      'publications', 'secret_key', 'start_year',
      'support_concurrency', 'support_datascheme',
      'support_durability', 'support_foreignkeys',
      'support_languages', 'support_mapreduce',
      'support_secondary', 'support_serverside', 'support_sql',
      'support_transactionconcepts', 'support_triggers',
      'support_typing', 'support_userconcepts', 'support_xml',
      'tech_docs', 'updated', 'website', 'written_in')

class OperatingSytemSerializer(serializers.ModelSerializer):
  class Meta:
    model = OperatingSystem
    fields = ('name')

class ProgrammingLanguageSerializer(serializers.ModelSerializer):
  class Meta:
    model = ProgrammingLanguage
    fields = ('name')