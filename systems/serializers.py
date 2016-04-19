from rest_framework import serializers
from systems.models import SystemVersion, OperatingSystem, ProgrammingLanguage

class SystemVersionSerializer(serializers.ModelSerializer):
  class Meta:
    model = SystemVersion
    fields = ('system','version_number','created','creator', 'version_message',
    'name','description','history','website','tech_docs','developer',
    'written_in','oses','publications','project_type','start_year','end_year',
    'derived_from','logo_img','dbmodel','license','access_methods',
    'support_systemarchitecture', 'feature_systemarchitecture',
    'support_datamodel', 'feature_datamodel',
    'support_storagemodel', 'feature_storagemodel',
    'support_queryinterface', 'feature_queryinterface',
    'support_storagearchitecture', 'feature_storagearchitecture',
    'support_concurrencycontrol', 'feature_concurrencycontrol',
    'support_isolationlevels', 'feature_isolationlevels',
    'support_indexes', 'feature_indexes',
    'support_foreignkeys', 'feature_foreignkeys',
    'support_logging', 'feature_logging',
    'support_checkpoints', 'feature_checkpoints',
    'support_views', 'feature_views',
    'support_queryexecution', 'feature_queryexecution',
    'support_storedprocedures', 'feature_storedprocedures',
    'support_joins', 'feature_joins',
    'support_querycompilation', 'feature_querycompilation',
    'support_languages','default_isolation','max_isolation',)

class LightSystemSerializer(serializers.ModelSerializer):
  class Meta:
    model = SystemVersion
    fields = ('id',
      'support_systemarchitecture',
      'support_datamodel',
      'support_storagemodel',
      'support_queryinterface',
      'support_storagearchitecture',
      'support_concurrencycontrol',
      'support_isolationlevels',
      'support_indexes',
      'support_foreignkeys',
      'support_logging',
      'support_checkpoints',
      'support_views',
      'support_queryexecution',
      'support_storedprocedures',
      'support_joins',
      'support_querycompilation',
      'name',)

class OperatingSystemSerializer(serializers.ModelSerializer):
  class Meta:
    model = OperatingSystem
    fields = ('name','website')

class ProgrammingLanguageSerializer(serializers.ModelSerializer):
  class Meta:
    model = ProgrammingLanguage
    fields = ('name','website')
