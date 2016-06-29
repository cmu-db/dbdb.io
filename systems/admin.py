from django.contrib import admin
from systems.models import *
from bibtexparser.bparser import BibTexParser
from pprint import pprint

class OperatingSystemAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'website', 'slug',)
    fieldsets = [
        (None,          {'fields': ['name', 'website']}),
    ]

class ProgrammingLanguageAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'website', 'slug',)
    fieldsets = [
        (None,          {'fields': ['name', 'website']}),
    ]

class LicenseAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'website',)

class DBModelAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'website',)

class APIAccessMethodsAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'website',)

class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors', 'year',)
    fieldsets = [
        (None,           {'fields': ['bibtex', 'download']}),
        ("Parsed Info",  {'fields': ['title', 'authors', ]}),
    ]
    readonly_fields = ('title', 'authors')

    def save_model(self, request, obj, form, change):
        bp = BibTexParser(obj.bibtex)
        bibtex = bp.get_entry_list()[0]
        obj.title = bibtex['title'].title()
        obj.authors = bibtex['author'].title()
        obj.year = bibtex['year']
        obj.save()

class SuggestedSystemAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'email', 'approved',)

class SystemAdmin(admin.ModelAdmin):
    """This class manages how system articles are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'created', 'current_version',)
    list_filter = ['created' ]
    fieldsets = [
        (None,          {'fields': ['name']}),
    ]

class FeatureOptionInline(admin.TabularInline):
    model = SystemVersionFeatureOption
    extra = 18

class SystemVersionAdmin(admin.ModelAdmin):
    """This class manages how system versions are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'version_number', 'created')
    list_filter = ['created']
    inlines = (FeatureOptionInline,)
    fieldsets = [
        (None,          {'fields': ['system', 'creator', 'version_message']}),
        ('Metadata',    {'fields': ['description', 'history', 'website', 'tech_docs',
                                    'developer', 'written_in', 'oses', 'publications',
                                    'project_type', 'start_year', 'end_year',
                                    'derived_from', 'logo_img', 'dbmodel', 'license',
                                    'access_methods', 'logo']}),
        ('Features',    {'fields': ['support_systemarchitecture', 'description_systemarchitecture',
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
                                    'support_querycompilation', 'description_querycompilation']}),
        ('Support',     {'fields': ['support_languages']}),
        ('Isolation',   {'fields': ['default_isolation', 'max_isolation']})
    ]

class FeatureAdmin(admin.ModelAdmin):
    """This class manages how features are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('label', 'multivalued')
    list_filter = ['label']

class FeatureOptionAdmin(admin.ModelAdmin):
    """This class manages how feature options are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('feature', 'value',)
    list_filter = ['feature']

class SystemVersionFeatureOptionAdmin(admin.ModelAdmin):
    """This class manages how feature options are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('system_version', 'feature_option',)
    list_filter = ['system_version', 'feature_option']

## CLASS
# Register your models here.
admin.site.register(OperatingSystem, OperatingSystemAdmin)
admin.site.register(ProgrammingLanguage, ProgrammingLanguageAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(DBModel, DBModelAdmin)
admin.site.register(APIAccessMethods, APIAccessMethodsAdmin)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(SuggestedSystem, SuggestedSystemAdmin)
admin.site.register(System, SystemAdmin)
admin.site.register(SystemVersion, SystemVersionAdmin)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(FeatureOption, FeatureOptionAdmin)
admin.site.register(SystemVersionFeatureOption, SystemVersionFeatureOptionAdmin)
