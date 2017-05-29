from rest_framework import serializers
from systems.models import License, OperatingSystem, ProgrammingLanguage, SystemVersion


class LicenseSerializer(serializers.ModelSerializer):
  class Meta:
    model = License
    fields = ('name', 'website', 'slug')


class OperatingSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatingSystem
        fields = ('name', 'website', 'slug')


class ProgrammingLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgrammingLanguage
        fields = ('name', 'website', 'slug')


class SystemVersionSerializer(serializers.ModelSerializer):
    oses = OperatingSystemSerializer(many=True)
    written_in = ProgrammingLanguageSerializer(many=True)
    licenses = LicenseSerializer(many=True)

    class Meta:
        model = SystemVersion
        fields = ('system', 'version_number', 'created', 'creator', 'version_message',
                  'name', 'description', 'history', 'website', 'tech_docs', 'developer',
                  'written_in', 'supported_languages', 'oses', 'publications', 'project_type', 'start_year',
                  'end_year', 'derived_from', 'logo_thumb', 'licenses',
                  'support_systemarchitecture', 'options_systemarchitecture', 'description_systemarchitecture',
                  'support_datamodel', 'options_datamodel', 'description_datamodel',
                  'support_storagemodel', 'options_storagemodel', 'description_storagemodel',
                  'support_queryinterface', 'options_queryinterface', 'description_queryinterface',
                  'support_storagearchitecture', 'options_storagearchitecture', 'description_storagearchitecture',
                  'support_concurrencycontrol', 'options_concurrencycontrol', 'description_concurrencycontrol',
                  'support_isolationlevels', 'options_isolationlevels', 'description_isolationlevels',
                  'support_indexes', 'options_indexes', 'description_indexes',
                  'support_foreignkeys', 'options_foreignkeys', 'description_foreignkeys',
                  'support_logging', 'options_logging', 'description_logging',
                  'support_checkpoints', 'options_checkpoints', 'description_checkpoints',
                  'support_views', 'options_views','description_views',
                  'support_queryexecution', 'options_queryexecution', 'description_queryexecution',
                  'support_storedprocedures', 'options_storedprocedures', 'description_storedprocedures',
                  'support_joins', 'options_joins', 'description_joins',
                  'support_querycompilation', 'options_querycompilation', 'description_querycompilation',
                  'support_accessmethods', 'options_accessmethods', 'description_accessmethods')


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
                  'support_accessmethods',
                  'name',)
