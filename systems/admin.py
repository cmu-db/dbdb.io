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
    list_filter = ['name', 'created', 'current_version']
    fieldsets = [
        (None,          {'fields': ['name']}),
    ]

class SystemVersionAdmin(admin.ModelAdmin):
    """This class manages how system versions are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'version_number', 'created')
    list_filter = ['name', 'version_number', 'created']
    fieldsets = [
        (None,          {'fields': ['system', 'creator', 'version_message']}),
        ('Metadata',    {'fields': ['description', 'history', 'website', 'tech_docs',
                                     'developer', 'written_in', 'oses', 'publications',
                                     'project_type', 'start_year', 'end_year', 'derived_from',
                                     'logo_img', 'dbmodel', 'license','access_methods',
                                     'logo']}),
        ('Features',    {'fields': ['support_concurrency', 'feature_concurrency',
                                     'support_datascheme', 'feature_datascheme',
                                     'support_durability', 'feature_durability',
                                     'support_foreignkeys', 'feature_foreignkeys',
                                     'support_mapreduce', 'feature_mapreduce',
                                     'support_querycompilation', 'feature_querycompilation',
                                     'support_secondaryindexes', 'feature_secondaryindexes',
                                     'support_serverside', 'feature_serverside',
                                     'support_sql', 'feature_sql',
                                     'support_transactionconcepts', 'feature_transactionconcepts',
                                     'support_triggers', 'feature_triggers',
                                     'support_typing', 'feature_typing',
                                     'support_userconcepts', 'feature_userconcepts',
                                     'support_xml', 'feature_xml']}),
        ('Support',     {'fields': ['support_languages']}),
        ('Isolation',   {'fields': ['default_isolation', 'max_isolation']})
    ]

class FeatureAdmin(admin.ModelAdmin):
    """This class manages how features are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('label', 'system_version', 'multivalued')
    list_filter = ['label', 'system_version']

class FeatureOptionAdmin(admin.ModelAdmin):
    """This class manages how feature options are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('feature', 'value',)
    list_filter = ['feature']

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
