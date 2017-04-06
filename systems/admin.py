from django.contrib import admin
from systems.models import *
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


class APIAccessMethodAdmin(admin.ModelAdmin):
    """Manages how API access methods are displayed
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
    list_filter = ['created']


class FeatureOptionInline(admin.TabularInline):
    """Manages how many feature options can be selected for a system version
    on the django administration page"""
    model = SystemVersionFeatureOption
    can_delete = False
    extra = 15  # 15 slots for choosing feature options


class SystemVersionAdmin(admin.ModelAdmin):
    """Manages how system versions are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('name', 'version_number', 'created')
    list_filter = ['name', 'created']
    inlines = (FeatureOptionInline,)
    fieldsets = [
        (None, {'fields': ['system', 'creator', 'version_message']}),
        ('Metadata', {'fields': ['description', 'history', 'website', 'tech_docs',
                                 'developer', 'written_in', 'oses', 'publications',
                                 'project_type', 'start_year', 'end_year',
                                 'derived_from', 'licenses',
                                 'access_methods', 'logo_orig', 'logo_thumb']}),
        ('Features', {'fields': ['support_systemarchitecture', 'description_systemarchitecture',
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
        ('Support', {'fields': ['support_languages']})
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


class SystemVersionFeatureOptionAdmin(admin.ModelAdmin):
    """Manages how feature options are displayed
    on the django administration page"""
    empty_value_display = 'unknown'
    list_display = ('system_version', 'feature_option',)
    list_filter = ['system_version', 'feature_option']


## CLASS
# Register your models here.
admin.site.register(OperatingSystem, OperatingSystemAdmin)
admin.site.register(ProgrammingLanguage, ProgrammingLanguageAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(APIAccessMethod, APIAccessMethodAdmin)
admin.site.register(Publication, PublicationAdmin)
admin.site.register(SuggestedSystem, SuggestedSystemAdmin)
admin.site.register(System, SystemAdmin)
admin.site.register(SystemVersion, SystemVersionAdmin)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(FeatureOption, FeatureOptionAdmin)
admin.site.register(SystemVersionFeatureOption, SystemVersionFeatureOptionAdmin)
