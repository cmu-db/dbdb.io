from django.contrib import admin
from systems.models import *
from bibtexparser.bparser import BibTexParser
from pprint import pprint

class OperatingSystemAdmin(admin.ModelAdmin):
    pass

class ProgrammingLanguageAdmin(admin.ModelAdmin):
    pass

class LicenseAdmin(admin.ModelAdmin):
    pass

class SuggestedSystemAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'email', 'approved')

class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors', 'year')
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

class SystemAdmin(admin.ModelAdmin):
    """docstring for SystemAdmin
    This class manages how systems are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'created', 'updated', 'current_version')

class SystemDataAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'version_number')


## CLASS
# Register your models here.
admin.site.register(OperatingSystem, OperatingSystemAdmin)
admin.site.register(ProgrammingLanguage, ProgrammingLanguageAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(SuggestedSystem, SuggestedSystemAdmin)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(System, SystemAdmin)
admin.site.register(SystemData, SystemDataAdmin)
