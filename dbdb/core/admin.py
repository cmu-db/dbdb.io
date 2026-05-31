# django imports
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.utils.html import format_html

# local imports
from .models import *

# ==============================================
# MIXINS
# ==============================================

class IconDisplayMixin:
    """Adds icon_display() and FontAwesome CSS Media to any ModelAdmin."""

    class Media:
        css = {'all': (settings.FONTAWESOME_CSS_URL,)}

    @admin.display(description='icon')
    def icon_display(self, obj):
        if not obj.icon:
            return ''
        return format_html('<i class="{}"></i> <tt>{}</tt>', obj.icon, obj.icon)

class CitationUrlAutocompleteMixin:
    """Replaces the default select widget with an incremental-search autocomplete
    for every ForeignKey field that points to CitationUrl.

    Requires CitationUrlAdmin to be registered with search_fields set (it is).
    Mix in before ModelAdmin in the MRO:  class MyAdmin(CitationUrlAutocompleteMixin, admin.ModelAdmin).
    """

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.related_model is CitationUrl:
            kwargs['widget'] = AutocompleteSelect(
                db_field,
                self.admin_site,
                using=kwargs.get('using'),
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ==============================================
# FLAT PAGES
# ==============================================

class FlatPageMetaInline(admin.StackedInline):
    model = FlatPageMeta
    can_delete = False
    verbose_name_plural = 'Display settings'

class FlatPageAdminWithMeta(FlatPageAdmin):
    inlines = [FlatPageMetaInline]

admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageAdminWithMeta)

# ==============================================
# USER
# ==============================================

class SystemACLInlines(admin.StackedInline):
    model = SystemACL
    extra = 0
    exclude=('created', 'modified')

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'date_joined', 'last_login')
    readonly_fields=('date_joined', 'last_login')
    inlines = [SystemACLInlines]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# ==============================================
# FEATURES
# ==============================================

class FeatureOptionsInlines(admin.StackedInline):
    model = FeatureOption
    extra = 0

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'option_count', 'modified')
    search_fields = ('label', 'slug')
    prepopulated_fields = {'slug': ('label',)}
    readonly_fields = ('created', 'modified')
    inlines = [FeatureOptionsInlines]

    @admin.display(description='options')
    def option_count(self, obj):
        return obj.options.count()

@admin.register(FeatureOption)
class FeatureOptionAdmin(admin.ModelAdmin):
    list_filter = ['feature']
    list_display = ('value', 'feature')
    search_fields = ('value', )

# ==============================================
# ATTRIBUTES
# ==============================================

class AttributeOptionInline(admin.TabularInline):
    model = AttributeOption
    extra = 0
    fields = ('name', 'slug', 'url', 'icon', 'description')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Attribute)
class AttributeAdmin(IconDisplayMixin, admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon_display', 'option_count', 'modified')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created', 'modified')
    inlines = [AttributeOptionInline]

    @admin.display(description='options')
    def option_count(self, obj):
        return obj.options.count()


@admin.register(AttributeOption)
class AttributeOptionAdmin(IconDisplayMixin, admin.ModelAdmin):
    list_display = ('name', 'slug', 'attribute', 'icon_display', 'url', 'modified')
    list_filter = ('attribute',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created', 'modified')
    ordering = ('attribute__name', 'name')

# ==============================================
# MISC
# ==============================================

@admin.register(CitationUrl)
class CitationUrlAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('id', 'url_display', 'status', 'last_title', 'last_statuscode', 'created', 'last_checked')
    search_fields = ('id', 'url', 'last_title')
    list_filter = ['status', 'created', 'last_checked', 'last_statuscode']

    @admin.display(description='url')
    def url_display(self, obj):
        return format_html('{} <a href="{}" target="_blank">🔗</a>', obj.url, obj.url)

@admin.register(Organization)
class OrganizationAdmin(CitationUrlAutocompleteMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'url', 'linkedin_url', 'created', 'modified')
    list_filter = ['created', 'modified']
    search_fields = ('name',)
    readonly_fields = ('created', 'modified')
    ordering = ('name',)

# ==============================================
# SYSTEMS
# ==============================================

@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('name', 'created', 'modified', 'ver', 'view_count', 'spotlight_enabled', 'spotlight_eligible')
    list_filter = ['created', 'modified', 'spotlight_enabled', 'spotlight_eligible']
    search_fields = ('name', )
    readonly_fields=('view_count', 'created', 'modified' )

@admin.register(SystemVersion)
class SystemVersionAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    raw_id_fields = ('description_citations', 'start_year_citations', 'end_year_citations', 'history_citations')
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

@admin.register(SavedSearch)
class SavedSearchAdmin(IconDisplayMixin, admin.ModelAdmin):
    list_display = ('name', 'icon_display', 'search_params', 'created', 'modified')
    list_filter = ['created', 'modified']
    search_fields = ('name', 'description')
    readonly_fields = ('created', 'modified')

# ==============================================
# URL MANAGEMENT
# ==============================================

class RepositorySnapshotInline(admin.TabularInline):
    model = RepositorySnapshot
    extra = 0
    max_num = 0       # no adding snapshots via inline
    can_delete = False
    show_change_link = True
    fields = (
        'created',
        'commit_count', 'last_commit_hash',
        'open_pr_count', 'merged_pr_count',
        'open_issue_count', 'closed_issue_count',
        'star_count', 'fork_count',
    )
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created')


@admin.register(RepositoryInfo)
class RepositoryInfoAdmin(CitationUrlAutocompleteMixin, admin.ModelAdmin):
    list_display = ('sourcerepo_url', 'enabled', 'last_snapshot', 'snapshot_count', 'created')
    list_filter = ('enabled', 'last_snapshot', 'modified')
    readonly_fields = ('created', 'modified', 'last_snapshot', 'current')
    search_fields = ('sourcerepo_url__url',)
    inlines = [RepositorySnapshotInline]

    @admin.display(description='snapshots')
    def snapshot_count(self, obj):
        return obj.snapshots.count()


@admin.register(RepositorySnapshot)
class RepositorySnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'repo', 'status',
        'last_commit_timestamp', 'commit_count',
        'open_pr_count', 'merged_pr_count',
        'open_issue_count', 'closed_issue_count',
        'star_count', 'fork_count',
        'branch_default_name', 'branch_count',
        'created',
    )
    list_filter = ('status', 'last_commit_timestamp', 'created',)
    readonly_fields = (
        'repo', 'created',
        'commit_count', 'last_commit_timestamp', 'last_commit_hash',
        'open_pr_count', 'merged_pr_count', 'last_pr_submitted_at', 'last_pr_closed_at',
        'open_issue_count', 'closed_issue_count', 'last_issue_submitted_at', 'last_issue_closed_at',
        'fork_count', 'star_count',
        'branch_count', 'branch_default_name', 'branch_name',
        'commit_authors', 'pr_authors', 'issue_authors',
    )
    ordering = ('-created',)
    search_fields = ('repo__sourcerepo_url__url',)


# ── Custom section ────────────────────────────────────────────────────────────
# Django admin groups by app_label, so "URL Management" models would normally
# appear under "Core".  We swap admin.site's class for a subclass that extracts
# those two models and re-injects them as a separate virtual section on the
# index page.  Existing registrations are untouched because we change the class
# on the live instance rather than creating a fresh AdminSite.

_URL_MGMT_MODELS = frozenset({'RepositoryInfo', 'RepositorySnapshot'})


class _DBDBAdminSite(admin.AdminSite):
    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)

        # Only reorganise on the top-level index (no app_label filter).
        if app_label is not None:
            return app_list

        url_models: list = []
        for app in app_list:
            if app['app_label'] == 'core':
                kept, moved = [], []
                for m in app['models']:
                    (moved if m['object_name'] in _URL_MGMT_MODELS else kept).append(m)
                app['models'] = kept
                url_models = moved
                break

        if url_models:
            app_list.append({
                'name': 'URL Management',
                'app_label': 'url_management',
                'app_url': '#',
                'has_module_perms': True,
                'models': url_models,
            })

        return app_list


admin.site.__class__ = _DBDBAdminSite