from rest_framework import serializers
from systems.models import System, OperatingSystem, ProgrammingLanguage

class SystemSerializer(serializers.ModelSerializer):
  class Meta:
    model = System
    fields = ('description', 'history', 'website', 'tech_docs', 'developer', 'written_in',
    'oses', 'publications', 'project_type', 'start_year', 'end_year', 'derived_from',
    'logo_img', 'dbmodel', 'license', 'access_methods', 'support_sql', 'description_sql',
    'support_foreignkeys', 'description_foreignkeys', 'support_serverside',
    'description_serverside', 'support_mapreduce', 'description_mapreduce',
    'support_secondary', 'description_secondary', 'support_durability', 'description_durability',
    'support_triggers','description_triggers','support_concurrency','description_concurrency',
    'support_datascheme','description_datascheme','support_xml','description_xml','support_typing',
    'description_typing','support_userconcepts','description_userconcepts','support_transactionconcepts',
    'description_transactionconcepts','support_querycompilation','description_querycompilation',
    'support_languages','default_isolation','max_isolation','secret_key','created','updated',
    'version','creator','version_message')

class LightSystemSerializer(serializers.ModelSerializer):
  class Meta:
    model = System
    fields = ( 'id',
      'support_concurrency', 'support_datascheme',
      'support_durability', 'support_foreignkeys',
      'support_languages', 'support_mapreduce',
      'support_secondary', 'support_serverside', 'support_sql',
      'support_transactionconcepts', 'support_triggers',
      'support_typing', 'support_userconcepts', 'support_xml', 'name')

class OperatingSystemSerializer(serializers.ModelSerializer):
  class Meta:
    model = OperatingSystem
    fields = ('name','website')

class ProgrammingLanguageSerializer(serializers.ModelSerializer):
  class Meta:
    model = ProgrammingLanguage
    fields = ('name','website')