from django.contrib import admin
from systems.models import *
from bibtexparser.bparser import BibTexParser
from pprint import pprint

class OperatingSystemAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'website', 'slug',)

class ProgrammingLanguageAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'website', 'slug',)

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

class SystemVersionAdmin(admin.ModelAdmin):
    """This class manages how system versions are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'version_number',)

class FeatureAdmin(admin.ModelAdmin):
    """This class manages how features are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('label', 'multivalued',)

class FeatureOptionAdmin(admin.ModelAdmin):
    """This class manages how feature options are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('system_version', 'feature', 'description',)

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
