from django.contrib import admin

from dbms_library.systems.models import *

# Register your models here.
admin.site.register(OperatingSystem)
admin.site.register(ProgrammingLanguage)
admin.site.register(System)