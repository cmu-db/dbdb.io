# django imports
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django.urls import reverse
from django.utils.html import format_html

# local imports
from .models import *
from .models import Acquisition

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
    fields = ('value', 'slug', 'description')

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'category', 'option_count', 'modified')
    search_fields = ('label', 'slug')
    prepopulated_fields = {'slug': ('label',)}
    readonly_fields = ('created', 'modified')
    fields = ('label', 'slug', 'category', 'multivalued', 'description', 'citations', 'created', 'modified')
    filter_horizontal = ('citations',)
    inlines = [FeatureOptionsInlines]

    @admin.display(description='options')
    def option_count(self, obj):
        return obj.options.count()

@admin.register(FeatureOption)
class FeatureOptionAdmin(admin.ModelAdmin):
    list_filter = ['feature']
    list_display = ('value', 'feature')
    search_fields = ('value', )
    fields = ('feature', 'value', 'slug', 'description', 'citations')
    filter_horizontal = ('citations',)

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
    filter_horizontal = ('citations',)
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
    filter_horizontal = ('citations',)

# ==============================================
# DOC PAGES
# ==============================================

class DocPageChildInline(admin.StackedInline):
    model = DocPage
    fk_name = 'parent'
    extra = 0
    fields = ('title', 'slug', 'sort_order', 'description', 'citations')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('citations',)

@admin.register(DocPage)
class DocPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'parent', 'sort_order', 'modified')
    list_filter = ('parent',)
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created', 'modified')
    fields = ('title', 'slug', 'parent', 'sort_order', 'description', 'citations', 'created', 'modified')
    filter_horizontal = ('citations',)
    inlines = [DocPageChildInline]

# ==============================================
# MISC
# ==============================================

@admin.register(CitationUrl)
class CitationUrlAdmin(admin.ModelAdmin):
    empty_value_display = 'unknown'
    list_display = ('id', 'url_display', 'status', 'last_title', 'last_statuscode', 'last_modified', 'last_checked')
    search_fields = ('id', 'url', 'last_title')
    list_filter = ['status', 'last_checked', 'last_modified', 'last_statuscode']

    @admin.display(description='url')
    def url_display(self, obj):
        return format_html('{} <a href="{}" target="_blank">🔗</a>', obj.url, obj.url)

class OrgDevelopedSystemsFilter(admin.SimpleListFilter):
    title = 'developed systems'
    parameter_name = 'developed_systems'

    def lookups(self, request, model_admin):
        return [('any', 'Has developed systems'), ('none', 'No developed systems')]

    def queryset(self, request, queryset):
        if self.value() == 'any':
            return queryset.filter(developed_systems__isnull=False).distinct()
        if self.value() == 'none':
            return queryset.filter(developed_systems__isnull=True)


class OrgAcquisitionsFilter(admin.SimpleListFilter):
    title = 'acquisitions'
    parameter_name = 'acquisitions'

    def lookups(self, request, model_admin):
        return [('any', 'Has acquisitions'), ('none', 'No acquisitions')]

    def queryset(self, request, queryset):
        if self.value() == 'any':
            return queryset.filter(acquisitions__isnull=False).distinct()
        if self.value() == 'none':
            return queryset.filter(acquisitions__isnull=True)


class OrgDeveloperOrgsInline(admin.TabularInline):
    """Read-only panel: SystemVersions that list this org as a developer."""
    model = SystemVersion.developer_orgs.through
    extra = 0
    max_num = 0
    can_delete = False
    verbose_name = "Developed System"
    verbose_name_plural = "Developed Systems"
    fields = ('system_link', 'version_label')
    readonly_fields = ('system_link', 'version_label')

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('systemversion__system')
            .order_by('systemversion__system__name', '-systemversion__ver')
        )

    @admin.display(description='System')
    def system_link(self, obj):
        sv = obj.systemversion
        url = reverse('admin:core_system_change', args=[sv.system_id])
        return format_html('<a href="{}">{}</a>', url, sv.system.name)

    @admin.display(description='Version')
    def version_label(self, obj):
        sv = obj.systemversion
        label = f"v{sv.ver}"
        return label + " (current)" if sv.is_current else label


class OrgAcquisitionInline(admin.TabularInline):
    """Read-only panel: Acquisitions where this org is the acquirer."""
    model = Acquisition
    extra = 0
    max_num = 0
    can_delete = False
    fields = ('system_link', 'year', 'citation')
    readonly_fields = ('system_link', 'year', 'citation')

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('version__system', 'citation')
            .order_by('version__system__name', 'year')
        )

    @admin.display(description='System')
    def system_link(self, obj):
        sv = obj.version
        url = reverse('admin:core_system_change', args=[sv.system_id])
        return format_html('<a href="{}">{}</a>', url, sv.system.name)


@admin.register(Organization)
class OrganizationAdmin(CitationUrlAutocompleteMixin, admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'url', 'linkedin_url', 'countries', 'stock_symbol', 'created', 'modified')
    list_filter = ['org_type', 'stock_exchange', 'created', 'modified', OrgDevelopedSystemsFilter, OrgAcquisitionsFilter]
    search_fields = ('name', 'stock_symbol')
    readonly_fields = ('created', 'modified')
    ordering = ('name',)
    inlines = [OrgDeveloperOrgsInline, OrgAcquisitionInline]

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
    list_display = ('system', 'ver', 'creator', 'approved', 'is_current', 'created')
    list_filter = ['created', 'approved', 'is_current', 'system']
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

@admin.register(SystemSuggestion)
class SystemSuggestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'system_url', 'email', 'is_my_system', 'created', 'approved_at', 'system', 'create_entry_button')
    list_filter = ['is_my_system', 'created', 'approved_at']
    search_fields = ('name', 'email', 'system_url')
    readonly_fields = ('created', 'modified')
    ordering = ('-created',)

    @admin.display(description='Action')
    def create_entry_button(self, obj):
        url = reverse('create_system') + f'?suggestion_id={obj.id}'
        return format_html('<a href="{}" class="button">Create Entry</a>', url)

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
    list_display = ('name', 'description', 'icon_display', 'search_params_link', 'created', 'modified')
    list_filter = ['created', 'modified']
    search_fields = ('name', 'description')
    readonly_fields = ('created', 'modified')

    @admin.display(description='search params')
    def search_params_link(self, obj):
        url = reverse('browse') + '?' + obj.search_params
        return format_html('<a href="{}" target="{}">{}🔗</a>', url, f"_search{obj.id}", obj.search_params)

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
        'commit_count', 'last_commit_timestamp',
        'open_pr_count', 'merged_pr_count',
        'open_issue_count', 'closed_issue_count',
        'star_count', 'fork_count',
    )
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created')


@admin.register(RepositoryInfo)
class RepositoryInfoAdmin(CitationUrlAutocompleteMixin, admin.ModelAdmin):
    list_display = ('sourcerepo_url', 'enabled', 'last_snapshot', 'snapshot_count', 'modified')
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
