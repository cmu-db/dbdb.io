from rest_framework import serializers
from systems.models import System, OperatingSystem, ProgrammingLanguage

class SystemSerializer(serializers.ModelSerializer):
  class Meta:
  	model = System
  	fields = ('name', 'description', 'website', 'developer', 'written_in',
  		'oses', 'publications', 'project_type', 'start_year', 'end_year',
  		'derived_from', 'support_sql', 'description_sql', 'support_foreignkeys',
      'description_foreignkeys', 'support_serverside', 'description_serverside',
  		'support_mapreduce', 'description_mapreduce', 'support_secondary', 'description_secondary',
      'support_durability', 'description_durability', 'support_triggers', 'description_triggers',
      'support_languages', 'default_isolation', 'support_concurrency',
      'description_concurrency', 'max_isolation')

class OperatingSytemSerializer(serializers.ModelSerializer):
  class Meta:
    model = OperatingSystem
    fields = ('name')

class ProgrammingLanguageSerializer(serializers.ModelSerializer):
  class Meta:
    model = ProgrammingLanguage
    fields = ('name')