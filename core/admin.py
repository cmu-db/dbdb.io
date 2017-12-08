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


admin.site.register(OperatingSystem)
admin.site.register(ProgrammingLanguage)
admin.site.register(License)
admin.site.register(ProjectType)
admin.site.register(Publication)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(FeatureOption)
admin.site.register(SuggestedSystem)
admin.site.register(System, SystemAdmin)
admin.site.register(SystemVersion)
admin.site.register(SystemVersionMetadata)
admin.site.register(SystemFeatures)