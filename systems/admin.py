from django.contrib import admin
from systems.models import OperatingSystem, ProgrammingLanguage, License, Publication, SuggestedSystem, \
    System, SystemVersion, Feature, FeatureOption
from bibtexparser.bparser import BibTexParser


class OperatingSystemAdmin(admin.ModelAdmin):
    """Manages how operating systems are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'website', 'slug',)
    fieldsets = [
        (None, {'fields': ['name', 'website']}),
    ]


class ProgrammingLanguageAdmin(admin.ModelAdmin):
    """Manages how programming languages are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'website', 'slug',)
    fieldsets = [
        (None, {'fields': ['name', 'website']}),
    ]


class LicenseAdmin(admin.ModelAdmin):
    """Manages how licenses are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'website',)


class PublicationAdmin(admin.ModelAdmin):
    """Manages how publications are displayed
    on the django administration page"""
    list_display = ('title', 'authors', 'year',)
    fieldsets = [
        (None, {'fields': ['bibtex', 'link']}),
        ("Parsed Info", {'fields': ['title', 'authors', ]}),
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
    """Manages how suggested systems are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'email', 'approved',)


class SystemAdmin(admin.ModelAdmin):
    """Manages how system articles are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'created', 'current_version',)
    search_fields = ('name', )
    list_filter = ['created', 'name']


class SystemVersionAdmin(admin.ModelAdmin):
    """Manages how system versions are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'version_number', 'created')
    search_fields = ('name', )
    list_filter = ['created', 'name']
    fieldsets = [
        (None, {'fields': ['system', 'creator', 'version_message']}),
        ('Metadata', {'fields': ['description', 'history', 'website', 'tech_docs',
                                 'developer', 'written_in', 'supported_languages',
                                 'oses', 'publications', 'project_type', 'start_year',
                                 'end_year', 'derived_from', 'licenses', 'logo_orig',
                                 'logo_thumb']}),
        ('Features', {'fields': ['support_systemarchitecture', 'options_systemarchitecture', 'description_systemarchitecture',
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
                                 'support_views', 'options_views', 'description_views',
                                 'support_queryexecution', 'options_queryexecution', 'description_queryexecution',
                                 'support_storedprocedures', 'options_storedprocedures', 'description_storedprocedures',
                                 'support_joins', 'options_joins', 'description_joins',
                                 'support_querycompilation', 'options_querycompilation', 'description_querycompilation',
                                 'support_accessmethods', 'options_accessmethods', 'description_accessmethods']})
    ]


class FeatureAdmin(admin.ModelAdmin):
    """Manages how features are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('label', 'multivalued')
    list_filter = ['label']


class FeatureOptionAdmin(admin.ModelAdmin):
    """Manages how feature options are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('feature', 'value',)
    list_filter = ['feature']

## CLASS
# Register your models here.
admin.site.register(OperatingSystem, OperatingSystemAdmin)
admin.site.register(ProgrammingLanguage, ProgrammingLanguageAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(SuggestedSystem, SuggestedSystemAdmin)
admin.site.register(System, SystemAdmin)
admin.site.register(SystemVersion, SystemVersionAdmin)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(FeatureOption, FeatureOptionAdmin)
