from django.contrib import admin

from .models import *


class FeatureOptionsInlines(admin.StackedInline):
    model = FeatureOption
    extra = 0


class FeatureAdmin(admin.ModelAdmin):
    inlines = [FeatureOptionsInlines]
    
class SystemAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'created', 'current_version',)
    list_filter = ['created' ]
    search_fields = ('name', )

class SystemVersionAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('system', 'version_number', 'created')
    list_filter = ['created']
    #inlines = (FeatureOptionsInlines,)
    #fieldsets = [
        #(None,          {'fields': ['system', 'creator', 'version_message']}),
        #('Metadata',    {'fields': ['description', 'history', 'website', 'tech_docs',
                                    #'developer', 'written_in', 'oses', 'publications',
                                    #'project_type', 'start_year', 'end_year',
                                    #'derived_from', 'logo_img', 'dbmodel', 'license',
                                    #'access_methods', 'logo']}),
        #('Features',    {'fields': ['support_systemarchitecture', 'description_systemarchitecture',
                                    #'support_datamodel', 'description_datamodel',
                                    #'support_storagemodel', 'description_storagemodel',
                                    #'support_queryinterface', 'description_queryinterface',
                                    #'support_storagearchitecture', 'description_storagearchitecture',
                                    #'support_concurrencycontrol', 'description_concurrencycontrol',
                                    #'support_isolationlevels', 'description_isolationlevels',
                                    #'support_indexes', 'description_indexes',
                                    #'support_foreignkeys', 'description_foreignkeys',
                                    #'support_logging', 'description_logging',
                                    #'support_checkpoints', 'description_checkpoints',
                                    #'support_views', 'description_views',
                                    #'support_queryexecution', 'description_queryexecution',
                                    #'support_storedprocedures', 'description_storedprocedures',
                                    #'support_joins', 'description_joins',
                                    #'support_querycompilation', 'description_querycompilation']}),
        #('Support',     {'fields': ['support_languages']}),
        #('Isolation',   {'fields': ['default_isolation', 'max_isolation']})
    #]


admin.site.register(OperatingSystem)
admin.site.register(ProgrammingLanguage)
admin.site.register(License)
admin.site.register(ProjectType)
admin.site.register(Publication)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(FeatureOption)
admin.site.register(SuggestedSystem)
admin.site.register(System, SystemAdmin)
admin.site.register(SystemVersion, SystemVersionAdmin)
admin.site.register(SystemVersionMetadata)
admin.site.register(SystemFeatures)