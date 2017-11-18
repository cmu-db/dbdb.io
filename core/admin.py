from django.contrib import admin

from .models import *

admin.site.register(OperatingSystem)
admin.site.register(ProgrammingLanguage)
admin.site.register(License)
admin.site.register(ProjectType)
admin.site.register(Publication)
admin.site.register(Feature)
admin.site.register(FeatureOption)
admin.site.register(SuggestedSystem)
admin.site.register(System)
admin.site.register(SystemVersion)
admin.site.register(SystemVersionMetadata)
admin.site.register(SystemFeatures)