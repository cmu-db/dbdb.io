from django.contrib import admin

from .models import *


class FeatureOptionsInlines(admin.StackedInline):
    model = FeatureOption
    extra = 0


class FeatureAdmin(admin.ModelAdmin):
    inlines = [FeatureOptionsInlines]


admin.site.register(OperatingSystem)
admin.site.register(ProgrammingLanguage)
admin.site.register(License)
admin.site.register(ProjectType)
admin.site.register(Publication)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(FeatureOption)
admin.site.register(SuggestedSystem)
admin.site.register(System)
admin.site.register(SystemVersion)
admin.site.register(SystemVersionMetadata)
admin.site.register(SystemFeatures)