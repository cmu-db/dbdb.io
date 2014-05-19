from django.contrib import admin

from systems.models import *

# Register your models here.
admin.site.register(OperatingSystem)
admin.site.register(ProgrammingLanguage)
admin.site.register(System)