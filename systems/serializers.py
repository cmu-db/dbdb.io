from rest_framework import serializers
from systems.models import SystemVersion, OperatingSystem, ProgrammingLanguage


class OperatingSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatingSystem
        fields = ('name', 'website', 'slug')


class ProgrammingLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgrammingLanguage
        fields = ('name', 'website', 'slug')


class LicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgrammingLanguage
        fields = ('name', 'website', 'slug')


class SystemVersionSerializer(serializers.ModelSerializer):
    oses = OperatingSystemSerializer(many=True)
    written_in = ProgrammingLanguageSerializer(many=True)
    license = LicenseSerializer(many=True)

    class Meta:
        model = SystemVersion
        fields = ('system', 'version_number', 'created', 'creator', 'version_message',
                  'name', 'description', 'history', 'website', 'tech_docs', 'developer',
                  'written_in', 'oses', 'publications', 'project_type', 'start_year', 'end_year',
                  'derived_from', 'logo_img', 'dbmodel', 'license', 'access_methods',
                  'support_systemarchitecture', 'description_systemarchitecture',
                  'support_datamodel', 'description_datamodel',
                  'support_storagemodel', 'description_storagemodel',
                  'support_queryinterface', 'description_queryinterface',
                  'support_storagearchitecture', 'description_storagearchitecture',
                  'support_concurrencycontrol', 'description_concurrencycontrol',
                  'support_isolationlevels', 'description_isolationlevels',
                  'support_indexes', 'description_indexes',
                  'support_foreignkeys', 'description_foreignkeys',
                  'support_logging', 'description_logging',
                  'support_checkpoints', 'description_checkpoints',
                  'support_views', 'description_views',
                  'support_queryexecution', 'description_queryexecution',
                  'support_storedprocedures', 'description_storedprocedures',
                  'support_joins', 'description_joins',
                  'support_querycompilation', 'description_querycompilation',
                  'support_languages', 'default_isolation', 'max_isolation',)


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
