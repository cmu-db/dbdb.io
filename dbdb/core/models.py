# django imports
import re
import tldextract
from colorfield.fields import ColorField
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django_countries.fields import CountryField

# third-party imports
from easy_thumbnails.fields import ThumbnailerField

from dbdb.core.common.searchvector import SearchVector
from dbdb.core.utils.logos import color_to_hex, extract_color, extract_dimensions


# ==============================================
# LogoMixin
# ==============================================
class LogoMixin(models.Model):
    logo = ThumbnailerField(blank=True, upload_to='logos/')
    logo_color = ColorField(format="hex", help_text="The color of the logo")
    logo_width = models.IntegerField(blank=True, null=True)
    logo_height = models.IntegerField(blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def logo_ext(self):
        import os
        if not self.logo:
            return ''
        return os.path.splitext(self.logo.name)[1].lstrip('.').upper()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # print(f"Logo({self.pk}) -> {self.logo} [{self.logo_color}]")
        if self.logo and self.logo_width is None:
            try:
                path = self.logo.path
                w, h = extract_dimensions(path)
                color = color_to_hex(extract_color(path))
                self.logo_width = w
                self.logo_height = h
                self.logo_color = color
                self.__class__.objects.filter(pk=self.pk).update(
                    logo_width=w,
                    logo_height=h,
                    logo_color=color,
                )
            except Exception:
                pass

# ==============================================
# CitationUrl
# ==============================================
class CitationUrl(models.Model):
    class Status(models.IntegerChoices):
        UNKNOWN = 0, "Unknown"
        VALID = 1, "Valid"
        DEAD = 2, "Dead"
        SPAM = 3, "Spam"
        IGNORE = 4, "Ignore"

    url = models.URLField(max_length=500, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=Status, blank=False, null=False, default=Status.UNKNOWN)
    last_checked = models.DateTimeField(default=None, blank=True, null=True)
    last_modified = models.DateTimeField(default=None, blank=True, null=True)
    last_title = models.CharField(max_length=250, default=None, blank=True, null=True)
    last_contenttype = models.CharField(max_length=100, default=None, blank=True, null=True)
    last_contentsize = models.PositiveIntegerField(default=None, blank=True, null=True)
    last_etag = models.CharField(max_length=100, default=None, blank=True, null=True)
    last_cachecontrol = models.JSONField(default=dict, blank=True, null=True)
    last_statuscode = models.PositiveIntegerField(default=None, blank=True, null=True)

    def get_domain(self, include_suffix:bool = True):
        if self.url.startswith('http'):
            extracted = tldextract.extract(self.url)
            domain = extracted.domain
            if include_suffix:
                domain += f".{extracted.suffix}"
            return domain
        return None

    class Meta:
        verbose_name = "Citation URL"

    def __str__(self):
        return f"#{self.id} ('{self.url}')"

    pass

# ==============================================
# Feature
# ==============================================
class Feature(models.Model):

    class Category(models.IntegerChoices):
        STORAGE_DATA             = 1, 'Storage & Data'
        QUERY_PROCESSING         = 2, 'Query Processing'
        TRANSACTIONS_CONCURRENCY = 3, 'Transactions & Concurrency'
        SYSTEM_RELIABILITY       = 4, 'System & Reliability'

    slug = models.SlugField(db_index=True, unique=True)
    label = models.CharField(max_length=100, unique=True)
    multivalued = models.BooleanField(default=True)
    description = models.TextField(blank=True, help_text='This field supports Markdown Syntax')
    category = models.IntegerField(choices=Category, blank=True, null=True)
    citations = models.ManyToManyField('CitationUrl', blank=True, related_name='features')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('label',)

    def __str__(self):
        return self.label

    def get_sanitized_label(self):
        return self.slug.lower().replace("-", "_")

    pass

# ==============================================
# FeatureOption
# ==============================================
class FeatureOption(models.Model):

    feature = models.ForeignKey('Feature', models.CASCADE, related_name='options')
    slug = models.SlugField(db_index=True, unique=False)
    value = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='', help_text='This field supports Markdown Syntax')
    citations = models.ManyToManyField('CitationUrl', blank=True, related_name='feature_options')

    class Meta:
        unique_together = ('feature','slug')

    def __str__(self):
        return self.value

    pass

# ==============================================
# Attribute
# ==============================================
class Attribute(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, help_text='This field supports Markdown Syntax')
    icon = models.CharField(max_length=64, blank=True)
    citations = models.ManyToManyField('CitationUrl', blank=True, related_name='attributes')
    sv_field = models.CharField(
        max_length=64, blank=True,
        verbose_name='SystemVersion field',
        help_text="Name of the SystemVersion M2M field (e.g. 'tags'). "
                  "Used to build browse filters automatically.")
    search_text = models.CharField(
        max_length=200, blank=True,
        help_text="Browse search description format string. Use {names} for the joined option names "
                  "(e.g. ' Tagged with {names}').")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    pass

# ==============================================
# AttributeOption
# ==============================================
class AttributeOption(models.Model):
    attribute = models.ForeignKey('Attribute', models.CASCADE, related_name='options')
    slug = models.SlugField()
    name = models.CharField(max_length=100)
    url = models.URLField(blank=True, max_length=512)
    description = models.TextField(blank=True, help_text='This field supports Markdown Syntax')
    icon = models.CharField(max_length=64, blank=True)
    citations = models.ManyToManyField('CitationUrl', blank=True, related_name='attribute_options')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        unique_together = ('attribute', 'slug')

    def __str__(self):
        return self.name

    pass


# ==============================================
# CitationUrlContent
# ==============================================
class CitationUrlContent(models.Model):
    citation = models.OneToOneField('CitationUrl', on_delete=models.CASCADE,
                                    related_name='content')
    raw  = models.TextField(blank=True, default='',
                            db_comment='Original HTML or PDF-extracted text from the crawled URL')
    text = models.TextField(blank=True, default='',
                            db_comment='Stripped, cleaned plain text for LLM context')
    created = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Citation URL Content"

    def __str__(self):
        return f"Content for citation #{self.citation_id}"

    pass


# ==============================================
# DocPage
# ==============================================
class DocPage(models.Model):
    slug        = models.SlugField(unique=True)
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='', help_text='This field supports Markdown Syntax')
    citations   = models.ManyToManyField('CitationUrl', blank=True, related_name='doc_pages')
    sort_order  = models.PositiveIntegerField(default=0)
    parent      = models.ForeignKey(
                      'self', null=True, blank=True,
                      related_name='children', on_delete=models.SET_NULL)
    created  = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title

    pass


# ==============================================
# SystemSuggestion
# ==============================================
class SystemSuggestion(models.Model):

    name = models.CharField(max_length=100)
    system_url = models.URLField(max_length=500)
    sourcerepo_url = models.URLField(blank=True, max_length=500)
    logo_url = models.URLField(blank=True, max_length=500)
    email = models.EmailField(max_length=100, blank=True)
    is_my_system = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    system = models.ForeignKey(
        'System', models.SET_NULL,
        null=True, blank=True,
        related_name='suggestions')

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return self.name

    pass

# ==============================================
# Organization
# ==============================================

class OrgType(models.IntegerChoices):
    COMPANY      = 1, 'Company'
    UNIVERSITY   = 2, 'University'
    INDIVIDUAL   = 3, 'Individual'
    RESEARCH_LAB = 4, 'Research Lab'
    NONPROFT     = 5, 'Non-profit Corporation'

    @property
    def icon(self):
        return {
            1: 'fa-solid fa-building',
            2: 'fa-solid fa-graduation-cap',
            3: 'fa-solid fa-person',
            4: 'fa-solid fa-flask',
            5: 'fa-solid fa-building-ngo',
        }.get(self.value, '')


class StockExchange(models.IntegerChoices):
    NYSE     = 1, 'NYSE'
    NASDAQ   = 2, 'NASDAQ'
    LSE      = 3, 'LSE'
    TSE      = 4, 'TSE'
    HKEX     = 5, 'HKEX'
    ASX      = 6, 'ASX'
    TSX      = 7, 'TSX'
    EURONEXT = 8, 'Euronext'
    OTHER    = 9, 'Other'

    @property
    def url(self):
        return {
            1: 'https://www.nyse.com',
            2: 'https://www.nasdaq.com',
            3: 'https://www.londonstockexchange.com',
            4: 'https://www.jpx.co.jp/english/',
            5: 'https://www.hkex.com.hk',
            6: 'https://www.asx.com.au',
            7: 'https://www.tsx.com',
            8: 'https://www.euronext.com',
        }.get(self.value, '')


class Organization(LogoMixin, models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200, unique=True)
    url = models.ForeignKey(
        'CitationUrl', models.SET_NULL,
        blank=True, null=True,
        related_name='org_urls',
        help_text="URL of the organization's main website")
    linkedin_url = models.ForeignKey(
        'CitationUrl', models.SET_NULL,
        blank=True, null=True,
        related_name='org_linkedin_urls',
        help_text="URL of the organization's LinkedIn page")

    org_type = models.IntegerField(
        choices=OrgType.choices, null=True, blank=True,
        verbose_name='Organization Type')

    stock_exchange = models.IntegerField(
        choices=StockExchange.choices, null=True, blank=True,
        verbose_name='Stock Exchange')

    stock_symbol = models.CharField(
        max_length=20, blank=True,
        help_text='Ticker symbol (e.g. ORCL, MSFT)')

    countries = CountryField(
        blank=True, multiple=True,
        verbose_name='Countries',
        help_text='Countries where this organization is headquartered')

    former_names = ArrayField(
        models.CharField(max_length=200),
        default=list, blank=True,
        help_text="Previous names this organization was known by")

    description = models.TextField(
        blank=True,
        help_text="This field supports Markdown Syntax")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def org_type_obj(self):
        return OrgType(self.org_type) if self.org_type is not None else None

    @property
    def stock_exchange_obj(self):
        return StockExchange(self.stock_exchange) if self.stock_exchange is not None else None

    def get_absolute_url(self):
        return reverse('organization', args=[self.slug])

# ==============================================
# System
# ==============================================
class System(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=64, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    ver = models.PositiveIntegerField('Version No.', default=1)
    spotlight_enabled = models.BooleanField(default=False)
    spotlight_eligible = models.BooleanField(default=False)

    class Meta:
        ordering = ('slug',)

    def __hash__(self):
        return hash((self.id, self.name, self.created, self.ver))

    def __str__(self):
        return self.name

    def current(self):
        if self.id is None:
            return SystemVersion(system=self)

        return self.versions.get(is_current=True)

    def pending_version(self):
        return self.versions.filter(approved=False).order_by('-created').first()

    def get_absolute_url(self):
        return reverse('system', args=[self.slug])

    pass

# ==============================================
# Acquisition
# ==============================================
class Acquisition(models.Model):
    version = models.ForeignKey(
        'SystemVersion', models.CASCADE,
        related_name='acquisitions')
    organization = models.ForeignKey(
        'Organization', models.PROTECT,
        related_name='acquisitions',
        help_text="The organization that acquired this system")
    year = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Year the acquisition was completed")
    citation = models.ForeignKey(
        'CitationUrl', models.SET_NULL,
        blank=True, null=True,
        related_name='acquisitions',
        help_text="Source documenting this acquisition")

    class Meta:
        ordering = ('year', 'organization__name')
        unique_together = ('version', 'organization')

    def __str__(self):
        year_str = f" ({self.year})" if self.year else ""
        return f"{self.version.system} acquired by {self.organization}{year_str}"

    pass

# ==============================================
# SystemACL
# ==============================================
class SystemACL(models.Model):
    system = models.ForeignKey('System', models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('system', 'user')
        verbose_name = "Permission"

    def __str__(self):
        return "(%s, %s)" % (self.system.name, self.user.username)

    pass

# ==============================================
# SystemFeature
# ==============================================
class SystemFeature(models.Model):

    version = models.ForeignKey('SystemVersion', models.CASCADE, related_name='features')
    feature = models.ForeignKey('Feature', models.CASCADE, related_name='system_features')

    citations = models.ManyToManyField('CitationUrl', related_name='system_features')
    options = models.ManyToManyField('FeatureOption', related_name='system_features')

    description = models.TextField(blank=True, help_text='This field supports Markdown Syntax')
    system = models.ForeignKey('System', models.CASCADE, blank=True, null=True, default=None,
                               help_text="Does this system inherit these features from another system")

    class Meta:
        unique_together = ('version','feature')

    def __str__(self):
        return f'{self.version} > {self.feature.label}'

    def values_str(self):
        return ', '.join([str(l) for l in self.options.all()])

    def get_my_or_parent_options(self) -> list:
        """Return the resolved FeatureOption list for this SystemFeature.

        If this instance has its own options, return them.
        If it delegates to a parent system, recurse into that system's
        corresponding SystemFeature.
        Otherwise return an empty list.
        """
        own = list(self.options.all())
        if own:
            return own
        if self.system is not None:
            try:
                parent_sf = SystemFeature.objects.get(
                    version=self.system.current(),
                    feature=self.feature,
                )
                return parent_sf.get_my_or_parent_options()
            except SystemFeature.DoesNotExist:
                pass
        return []

    def clean(self):
        super().clean()
        # Make sure the derived system feature is *not* the same as this system
        if self.system is not None:
            if self.version.system == self.system:
                raise ValidationError(f"Cannot set feature's derived system ({self.system} as the same system {self.version.system}")

    def save(self, *args, **kwargs):
        self.full_clean()  # runs `clean()`, field validation, unique checks
        super().save(*args, **kwargs)

    pass

# ==============================================
# SystemRedirect
# ==============================================
class SystemRedirect(models.Model):

    system = models.ForeignKey('System', models.CASCADE, related_name='redirects')

    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    pass

# ==============================================
# SystemVisit
# ==============================================
class SystemVisit(models.Model):
    system = models.ForeignKey('System', models.CASCADE, related_name='visits')
    ip_address = models.GenericIPAddressField(null=False)
    user_agent = models.CharField(max_length=128, blank=True, null=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "(%s, %s, %s)" % (self.system.name, self.ip_address, str(self.created))

    class Meta:
        verbose_name = "Visit"

    pass

# ==============================================
# SystemRecommendation
# ==============================================
class SystemRecommendation(models.Model):
    system = models.ForeignKey('System', models.CASCADE, related_name='recommendation_to')
    recommendation = models.ForeignKey('System', models.CASCADE, related_name='recommendation_from')
    score = models.FloatField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "(%s, %s)" % (self.system.name, self.recommendation.name)

    class Meta:
        verbose_name = "Recommendation"
        unique_together = ('system', 'recommendation')

    pass

# ==============================================
# SystemSearchText
# ==============================================
class SystemSearchText(models.Model):
    system = models.OneToOneField(System, on_delete=models.CASCADE, primary_key=True)
    name = models.CharField(max_length=64, blank=False, null=False)
    search_text = models.TextField(default=None, null=True,
                                   help_text="Synthesized text for searching")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "System Search Text"
        indexes = [
            GinIndex(SearchVector("search_text", config="simple"), name="core_system_search__cf51c1_gin", fastupdate=False)
        ]

    pass

# ==============================================
# SystemVersion
# ==============================================
class SystemVersion(LogoMixin, models.Model):

    # Internal Version Meta-data
    system = models.ForeignKey('System', models.CASCADE, related_name='versions')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    ver = models.PositiveIntegerField('Version No.', default=1)
    is_current = models.BooleanField(default=True)
    approved = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    # Fields with citations
    description = models.TextField(
        blank=True,
        help_text="This field support Markdown Syntax")
    description_citations = models.ManyToManyField(
        'CitationUrl', blank=True,
        related_name='version_descriptions')

    start_year = models.PositiveIntegerField(
        blank=True, null=True)
    start_year_citations = models.ManyToManyField(
        'CitationUrl', blank=True,
        related_name='version_start_years')

    end_year = models.PositiveIntegerField(
        blank=True, null=True)
    end_year_citations = models.ManyToManyField(
        'CitationUrl', blank=True,
        related_name='version_end_years')

    history = models.TextField(
        blank=True,
        help_text="This field support Markdown Syntax")
    history_citations = models.ManyToManyField(
        'CitationUrl', blank=True,
        related_name='version_histories')

    # General Information Fields
    developer_orgs = models.ManyToManyField(
        'Organization', blank=True,
        related_name='developed_systems',
        verbose_name='Developer Organizations',
        help_text="Organizations that developed this DBMS (structured alternative to the developer text field)")

    countries = CountryField(
        blank=True, multiple=True,
        verbose_name="Countries of Origin",
        help_text="Country of where the DBMS company or project started")

    former_names = ArrayField(
        models.CharField(max_length=200),
        default=list, blank=True,
        help_text="Previous names of the system")

    system_url = models.ForeignKey(
        'CitationUrl', blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='version_system_urls',
        verbose_name="Website URL")

    docs_url = models.ForeignKey(
        'CitationUrl', blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='version_docs_urls',
        verbose_name="Tech Docs URL")

    sourcerepo_url = models.ForeignKey(
        'CitationUrl', blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='version_sourcerepo_urls',
        verbose_name="Source Code URL")

    wikipedia_url = models.ForeignKey(
        'CitationUrl', blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='version_wikipedia_urls',
        verbose_name="Wikipedia URL")

    linkedin_url = models.ForeignKey(
        'CitationUrl', blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='version_linkedin_urls',
        verbose_name="LinkedIn URL")

    twitter_handle = models.CharField(
        blank=True, max_length=100,
        help_text="Twitter account for the database (avoid company account if possible)")

    derived_from = models.ManyToManyField(
        'System', blank=True,
        related_name='derived_from_systems',
        verbose_name='Systems Derived From',
        help_text="Systems that this system's source code is based on")

    embedded = models.ManyToManyField(
        'System', blank=True,
        related_name='embedded_systems',
        verbose_name='Systems Embedded',
        help_text="Systems that this system uses on the inside (e.g., storage manager)")

    inspired_by = models.ManyToManyField(
        'System', blank=True,
        related_name='inspired_by_systems',
        verbose_name='Systems Inspired By',
        help_text="Systems used for inspiration in its design but did not rely on source code")

    compatible_with = models.ManyToManyField(
        'System', blank=True,
        related_name='compatible_with_systems',
        verbose_name='Systems Compatible With',
        help_text="Other systems that this system is compatible with (e.g., wire protocol, file formats).")

    hosted_services = models.ManyToManyField(
        'System', blank=True,
        related_name='hosted_by_systems',
        verbose_name='Hosted DBaaS Services',
        help_text="Other DBMS systems that this system offers as a managed hosted DBaaS service (e.g., Amazon RDS hosting PostgreSQL). Do not include this system itself.")

    governance = models.ManyToManyField(
        'AttributeOption', blank=True,
        limit_choices_to={'attribute__slug': 'governance'},
        related_name='system_governance',
        verbose_name='Governance')

    tags = models.ManyToManyField(
        'AttributeOption', blank=True,
        limit_choices_to={'attribute__slug': 'tag'},
        related_name='system_tags',
        verbose_name='Tags')

    project_types = models.ManyToManyField(
        'AttributeOption', blank=True,
        limit_choices_to={'attribute__slug': 'project-type'},
        related_name='system_project_types',
        verbose_name='Project Types')

    licenses = models.ManyToManyField(
        'AttributeOption', blank=True,
        limit_choices_to={'attribute__slug': 'license'},
        related_name='system_licenses',
        verbose_name='Licenses')

    oses = models.ManyToManyField(
        'AttributeOption', blank=True,
        limit_choices_to={'attribute__slug': 'os'},
        related_name='system_oses',
        verbose_name='Operating Systems')

    supported_languages = models.ManyToManyField(
        'AttributeOption', blank=True,
        limit_choices_to={'attribute__slug': 'programming-language'},
        related_name='system_supported_languages',
        verbose_name='Supported Languages')

    written_in = models.ManyToManyField(
        'AttributeOption', blank=True,
        limit_choices_to={'attribute__slug': 'programming-language'},
        related_name='system_written_in',
        verbose_name='Written In')

    class Meta:
        ordering = ('-ver',)
        unique_together = ('system', 'ver')
        constraints = [
            models.UniqueConstraint(
                fields=['system'],
                condition=models.Q(approved=False),
                name='unique_pending_version_per_system',
            ),
        ]

    def __hash__(self):
        return hash((
            self.created,
            self.id,
            self.system,
            self.ver,
        ))

    def __str__(self):
        return f'{self.system.name} - Ver#{self.ver}'

    def get_absolute_url(self):
        return reverse('system_version', args=[self.system.slug, self.ver])

    def get_diff_url(self):
        return reverse('system_diff', args=[self.system.slug, self.system.current().ver, self.ver])

    def tags_str(self):
        return ', '.join( self.tags.values_list('name', flat=True) )

    def project_types_str(self):
        return ', '.join( self.project_types.values_list('name', flat=True) )

    def derived_from_str(self):
        return ', '.join([str(l) for l in self.derived_from.all()])

    def embedded_str(self):
        return ', '.join([str(l) for l in self.embedded.all()])

    def compatible_with_str(self):
        return ', '.join([str(l) for l in self.compatible_with.all()])

    def inspired_by_str(self):
        return ', '.join([str(l) for l in self.inspired_by.all()])

    def licenses_str(self):
        return ', '.join([str(l) for l in self.licenses.all()])

    def oses_str(self):
        return ', '.join([str(l) for l in self.oses.all()])

    def supported_languages_str(self):
        return ', '.join([str(l) for l in self.supported_languages.all()])

    def written_in_str(self):
        return ', '.join([str(l) for l in self.written_in.all()])

    def description_mobile_intro(self):
        return self.description.split("\n")[0]

    def description_mobile_remainder(self):
        return "\n".join(self.description.split("\n")[1:])

    @property
    def linkedin_handle(self):
        if not self.linkedin_url_id:
            return None
        m = re.search(r'linkedin\.com(.*)', self.linkedin_url.url)
        if not m:
            return None
        return m.group(1).rstrip('/')

    def twitter_handle_url(self):
        if not self.twitter_handle: return None
        return settings.TWITTER_URL + self.twitter_handle.replace('@', '')

    def twitter_card_url(self):
        return settings.TWITTER_CARD_URL + self.get_twitter_card_image()

    def get_twitter_card_image(self):
        return self.system.slug + ".png"

    pass


# ==============================================
# SavedSearch
# ==============================================
class SavedSearch(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=100, blank=True, help_text="FontAwesome class, e.g. 'fas fa-database'")
    search_params = models.CharField(max_length=1000, help_text="Query string for the browse URL, e.g. 'data-model=relational'")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Saved Search'
        verbose_name_plural = 'Saved Searches'

    def __str__(self):
        return self.name


# ==============================================
# FlatPageMeta
# ==============================================
class FlatPageMeta(models.Model):
    """Extends django.contrib.flatpages.FlatPage with site-specific metadata."""
    page = models.OneToOneField(
        'flatpages.FlatPage',
        on_delete=models.CASCADE,
        related_name='meta',
    )
    show_in_navbar = models.BooleanField(
        default=False,
        help_text="Show this page as a link in the top navigation bar.",
    )
    nav_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Order in which this page appears in the navbar (lower = first).",
    )
    kicker = models.CharField(
        max_length=100,
        blank=True,
        help_text="Short label shown above the page title (e.g. 'About', 'Resources').",
    )
    subtitle = models.CharField(
        max_length=255,
        blank=True,
        help_text="Italic subheading shown below the page title.",
    )
    modified = models.DateTimeField(
        auto_now=True,
        help_text="Automatically updated whenever this record is saved.",
    )

    class Meta:
        ordering = ['nav_order', 'page__title']

    def __str__(self):
        return f"Meta for {self.page}"


# ==============================================
# RepositoryInfo
# ==============================================
class RepositoryInfo(models.Model):
    sourcerepo_url = models.OneToOneField(
        'CitationUrl', models.CASCADE,
        related_name='repository_info',
        verbose_name="Source Repository URL")
    current = models.ForeignKey(
        'RepositorySnapshot', models.SET_NULL,
        blank=True, null=True,
        related_name='+',
        verbose_name="Current Snapshot")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    last_snapshot = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp of the last time this repository was scanned")
    enabled = models.BooleanField(
        default=True,
        help_text="Whether this repository should be scanned for new snapshots")

    class Meta:
        verbose_name = "Repository Info"
        verbose_name_plural = "Repository Infos"

    def __str__(self):
        return f"RepositoryInfo({self.sourcerepo_url.url})"


# ==============================================
# RepositorySnapshot
# ==============================================
class RepositorySnapshot(models.Model):
    class Status(models.IntegerChoices):
        UNKNOWN = 0, "Unknown"
        VALID   = 1, "Valid"
        ERROR   = 2, "Error"
        FAILED  = 3, "Failed"

    repo = models.ForeignKey(
        'RepositoryInfo', models.CASCADE,
        related_name='snapshots')
    created = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(
        choices=Status,
        blank=False, null=False,
        default=Status.UNKNOWN,
        help_text="Outcome of the snapshot retrieval attempt")

    # Commit statistics
    commit_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Total number of commits on the default branch")
    last_commit_timestamp = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp of the most recent commit")
    last_commit_hash = models.CharField(
        max_length=64, blank=True,
        help_text="SHA hash of the most recent commit")

    # Pull request statistics
    open_pr_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Number of currently open pull requests / merge requests")
    merged_pr_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Total number of merged pull requests / merge requests")
    last_pr_submitted_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp of the most recently submitted (opened) pull request")
    last_pr_closed_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp of the most recently closed or merged pull request")

    # Issue statistics
    open_issue_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Number of currently open issues")
    closed_issue_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Total number of closed issues")
    last_issue_submitted_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp of the most recently submitted (opened) issue")
    last_issue_closed_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp of the most recently closed issue")

    # Branch statistics
    branch_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Total number of branches in the repository")
    branch_default_name = models.CharField(
        max_length=255, blank=True,
        help_text="Name of the repository's default branch")
    branch_names = ArrayField(
        models.CharField(max_length=255),
        default=list, blank=True,
        help_text="Names of up to 100 branches (most recent / alphabetical order)")

    # Popularity statistics
    fork_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Number of repository forks")
    star_count = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Number of repository stars / watchers")

    # Archival status
    archival_timestamp = models.DateTimeField(
        blank=True, null=True,
        help_text="Timestamp when the repository was archived, if applicable (GitHub only)")

    # Contributor lists
    commit_authors = ArrayField(
        models.CharField(max_length=254),
        default=list, blank=True,
        help_text="Unique contributor login names or display names (from commit history)")
    pr_authors = ArrayField(
        models.CharField(max_length=255),
        default=list, blank=True,
        help_text="Unique authors who have submitted pull requests or merge requests")
    issue_authors = ArrayField(
        models.CharField(max_length=255),
        default=list, blank=True,
        help_text="Unique authors who have submitted issues")

    class Meta:
        verbose_name = "Repository Snapshot"
        ordering = ('-created',)

    def __str__(self):
        return f"RepositorySnapshot({self.repo_id}, {self.created})"


__all__ = (
    'Attribute',
    'AttributeOption',
    'CitationUrl',
    'CitationUrlContent',
    'DocPage',
    'Feature',
    'FeatureOption',
    'FlatPageMeta',
    'Organization',
    'RepositoryInfo',
    'RepositorySnapshot',
    'SavedSearch',
    'SystemSuggestion',
    'System',
    'SystemFeature',
    'SystemVersion',
    'SystemACL',
    'SystemRecommendation',
    'SystemSearchText',
    'SystemVisit',
    'user_can_edit_system',
)

def user_can_edit_system(user, system):
    """Return True if the user is allowed to edit the given System."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return SystemACL.objects.filter(system=system, user=user).exists()


# signal handlers
@receiver(pre_save, sender=SystemVersion)
def systemversion_pre_save(sender, **kwargs):
    instance = kwargs['instance']
    update_fields = kwargs['update_fields']

    created = instance.id is None

    if created:
        aggregates = SystemVersion.objects.filter(system=instance.system).aggregate(max_ver=Max('ver'))
        max_ver = aggregates['max_ver']

        if max_ver is None:
            instance.ver = 1
            instance.is_current = True
            instance.approved = True
        else:
            instance.ver = max_ver + 1
            if instance.approved:
                # Approved: make this the live version.
                SystemVersion.objects.filter(system=instance.system).update(is_current=False)
                instance.is_current = True
            else:
                # Pending: do NOT flip existing versions; stay invisible.
                instance.is_current = False

        if instance.approved:
            instance.system.ver = instance.ver
            instance.system.save()

    return
