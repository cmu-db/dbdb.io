from django.contrib import admin
from systems.models import *
from bibtexparser.bparser import BibTexParser
from pprint import pprint

# Register your models here.
admin.site.register(OperatingSystem)
admin.site.register(ProgrammingLanguage)
admin.site.register(License)
admin.site.register(System)
admin.site.register(SystemManager)
admin.site.register(SuggestedSystem)


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
## CLASS
admin.site.register(Publication, PublicationAdmin)