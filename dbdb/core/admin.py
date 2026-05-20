# django imports
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html

# local imports
from .models import *

class FeatureOptionsInlines(admin.StackedInline):
    model = FeatureOption
    extra = 0

class SystemACLInlines(admin.StackedInline):
    model = SystemACL
    extra = 0
    exclude=('created', 'modified')

# model admins

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'date_joined', 'last_login')
    readonly_fields=('date_joined', 'last_login')
    inlines = [SystemACLInlines]

@admin.register(CitationUrl)
class CitationUrlAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('id', 'url', 'status', 'last_title', 'last_statuscode', 'created', 'last_checked')
    search_fields = ('id', 'url', 'last_title')
    list_filter = ['status', 'created', 'last_checked', 'last_statuscode']

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    inlines = [FeatureOptionsInlines]

@admin.register(FeatureOption)
class FeatureOptionAdmin(admin.ModelAdmin):
    list_filter = ['feature']
    list_display = ('value', 'feature')
    search_fields = ('value', )

@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'created', 'modified', 'ver', 'view_count')
    list_filter = ['created', 'modified' ]
    search_fields = ('name', )
    readonly_fields=('view_count', 'created', 'modified' )

@admin.register(SystemVersion)
class SystemVersionAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    raw_id_fields = ('description_citations', 'start_year_citations', 'end_year_citations', 'history_citations', 'acquired_by_citations')
    list_display = ('system', 'ver', 'creator', 'created')
    list_filter = ['created', 'system']
    readonly_fields=('ver', 'system')
    ordering = ('-created',)
    exclude = ('system', )

@admin.register(SystemFeature)
class SystemFeatureAdmin(admin.ModelAdmin):
    search_fields = ('id',)

@admin.register(SystemACL)
class SystemACLAdmin(admin.ModelAdmin):
    list_display = ('system', 'user', 'created', 'modified')
    list_filter = ['created']
    readonly_fields=('created', 'modified')

@admin.register(SystemRecommendation)
class SystemRecommendationAdmin(admin.ModelAdmin):
    list_display = ('system', 'recommendation', 'score', 'created')
    list_filter = ['created', 'system']
    readonly_fields=('created', )
    ordering = ('-created',)

@admin.register(SystemSearchText)
class SystemSearchTextAdmin(admin.ModelAdmin):
    list_display = ('system', 'search_text', 'created')
    readonly_fields = ('created',)
    ordering = ('-created',)
    search_fields = ('system__name',)

@admin.register(SystemVisit)
class SystemVisitAdmin(admin.ModelAdmin):
    list_display = ('system', 'ip_address', 'created')
    list_filter = ['created', 'system']
    readonly_fields=('created',)
    ordering = ('-created',)

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'url')
    ordering = ('name',)

@admin.register(OperatingSystem)
class OperatingSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'url')
    ordering = ('name',)

@admin.register(ProgrammingLanguage)
class ProgrammingLanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'url')
    ordering = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon_display', 'url')
    ordering = ('name',)

    class Media:
        css = {'all': ('//use.fontawesome.com/releases/v7.1.0/css/all.css',)}

    @admin.display(description='icon')
    def icon_display(self, obj):
        if not obj.icon:
            return ''
        return format_html('<i class="{}"></i> <tt>{}</tt>', obj.icon, obj.icon)

# registrations
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(ProjectType)
