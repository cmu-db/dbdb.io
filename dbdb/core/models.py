# stdlib imports
import uuid
# django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Max
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
# third-party imports
from easy_thumbnails.fields import ThumbnailerImageField
from django_countries.fields import CountryField


# ==============================================
# CitationUrl
# ==============================================
class CitationUrl(models.Model):

    url = models.URLField(max_length=500)

    def __str__(self):
        return self.url

    pass

# ==============================================
# Feature
# ==============================================
class Feature(models.Model):

    slug = models.SlugField(db_index=True, unique=True)
    label = models.CharField(max_length=100, unique=True)
    multivalued = models.BooleanField(default=True)

    class Meta:
        ordering = ('label',)

    def __str__(self):
        return self.label

    pass

# ==============================================
# FeatureOption
# ==============================================
class FeatureOption(models.Model):

    feature = models.ForeignKey('Feature', models.CASCADE, related_name='options')

    slug = models.SlugField(db_index=True, unique=False)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ('feature','slug')

    def __str__(self):
        return self.value

    pass

# ==============================================
# License
# ==============================================
class License(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=32)
    url = models.URLField(blank=True, max_length=512)

    class Meta:
        ordering = ('name',)


    def __str__(self):
        return self.name

    pass

# ==============================================
# OperatingSystem
# ==============================================
class OperatingSystem(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    url = models.URLField(blank=True, max_length=500)

    class Meta:
        ordering = ('name',)


    def __str__(self):
        return self.name

    pass

# ==============================================
# ProgrammingLanguage
# ==============================================
class ProgrammingLanguage(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    url = models.URLField(blank=True, max_length=500)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    pass

# ==============================================
# ProjectType
# ==============================================
class ProjectType(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=32)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    pass

# ==============================================
# Publication
# ==============================================
class Publication(models.Model):

    title = models.CharField(max_length=250)
    authors = models.CharField(blank=True, max_length=250)
    year = models.PositiveIntegerField(blank=True, null=True)
    number = models.IntegerField(default=1, null=True)
    url = models.URLField(blank=True, max_length=500)

    bibtex = models.TextField(blank=True)
    cite = models.TextField(blank=True)

    def __str__(self):
        return self.title

    pass

# ==============================================
# SuggestedSystem
# ==============================================
class SuggestedSystem(models.Model):

    name = models.CharField(max_length=100)
    description = models.TextField(default=None, null=True, blank=True)
    email = models.EmailField(max_length=100)
    approved = models.BooleanField()
    secret_key = models.UUIDField(max_length=36, default=uuid.uuid4)
    url = models.URLField(blank=True, max_length=500)

    class Meta:
        ordering = ('name',)


    def __str__(self):
        return self.name

    pass

# ==============================================
# System
# ==============================================
class System(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=64, blank=False)
    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)
    secret_key = models.UUIDField(max_length=36, default=uuid.uuid4)
    view_count = models.PositiveIntegerField(default=0)
    ver = models.PositiveIntegerField('Version No.', default=1)

    class Meta:
        ordering = ('slug',)

    def __hash__(self):
        return hash((
            self.id,
            self.name,
            self.created,
            self.ver,
            self.secret_key
        ))

    def __str__(self):
        return self.name

    def current(self):
        if self.id is None:
            return SystemVersion(system=self)

        return self.systemversion_set.get(is_current=True)

    def get_absolute_url(self):
        return reverse('system', args=[self.slug])

    pass

# ==============================================
# SystemACL
# ==============================================
class SystemACL(models.Model):
    system = models.ForeignKey('System', models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)

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

    system = models.ForeignKey('SystemVersion', models.CASCADE, related_name='features')
    feature = models.ForeignKey('Feature', models.CASCADE, related_name='system_features')

    citations = models.ManyToManyField('CitationUrl', related_name='system_features')
    options = models.ManyToManyField('FeatureOption', related_name='system_features')

    description = models.TextField(blank=True, help_text='This field supports Markdown Syntax')

    class Meta:
        unique_together = ('system','feature')

    def __str__(self):
        return '{} > {}'.format(self.system.system.name, self.feature.label)

    def values_str(self):
        return ', '.join([str(l) for l in self.options.all()])

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
    system = models.ForeignKey('System', models.CASCADE, related_name='counter')
    ip_address = models.GenericIPAddressField(null=False)
    user_agent = models.CharField(max_length=128, blank=True, null=False)
    created = models.DateTimeField(default=timezone.now)
    
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
    created = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return "(%s, %s)" % (self.system.name, self.recommendation.name)

    class Meta:
        verbose_name = "Recommendation"

    pass

# ==============================================
# SystemVersion
# ==============================================
class SystemVersion(models.Model):

    # Internal Version Meta-data
    system = models.ForeignKey('System', models.CASCADE)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    meta = models.ForeignKey('SystemVersionMetadata', models.SET_NULL, blank=True, null=True)
    ver = models.PositiveIntegerField('Version No.', default=1)
    is_current = models.BooleanField(default=True)
    comment = models.TextField(blank=True)
    created = models.DateTimeField(default=timezone.now)

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

    acquired_by = models.CharField(
        blank=True, max_length=32,
        help_text="Name of the company that first acquired the DBMS")
    acquired_by_citations = models.ManyToManyField(
        'CitationUrl', blank=True,
        related_name='version_acquired_bys')

    # General Information Fields
    project_types = models.ManyToManyField(
        'ProjectType', blank=True,
        related_name='project_types',
        verbose_name='Project Type')

    developer = models.CharField(
        blank=True, max_length=500,
        help_text="The original organization that developed the DBMS.")

    logo = ThumbnailerImageField(
        blank=True, upload_to='logos/')

    countries = CountryField(
        blank=True, multiple=True,
        verbose_name="Countries of Origin",
        help_text="Country of where the DBMS company or project started")

    former_names = models.CharField(
        blank=True, max_length=100,
        help_text="Previous names of the system")

    # URLs
    url = models.URLField(
        blank=True, max_length=500,
        help_text="URL of the DBMS company or project")

    tech_docs = models.URLField(
        blank=True, max_length=500,
        help_text="URL of the where to find technical documentation about the DBMS")

    source_url = models.URLField(
        blank=True, max_length=500,
        verbose_name="Source Code URL",
        help_text="URL of where to download source code (if available)")

    wikipedia_url = models.URLField(
        blank=True, max_length=500,
        verbose_name="Wikipedia URL",
        help_text="URL of Wikipedia article about this system (if available)")

    class Meta:
        ordering = ('-ver',)
        unique_together = ('system','ver')

    def __hash__(self):
        return hash((
            self.created,
            self.id,
            self.system,
            self.ver,
        ))

    def __str__(self):
        return '{} - Ver#{}'.format(self.system.name, self.ver)

    def get_absolute_url(self):
        return reverse('system_revision_view', args=[self.system.slug, self.ver])

    def project_types_str(self):
        return ', '.join( self.project_types.values_list('name', flat=True) )

    def update_version(self):
        created = self.id is None

        if created:
            aggregates = SystemVersion.objects.filter(system=instance.system).aggregate(max_ver=Max('ver'))
            max_ver = aggregates['max_ver']

            if max_ver is None:
                instance.ver = 1
                pass
            else:
                SystemVersion.objects.filter(system=instance.system).update(is_current=False)
                instance.ver = max_ver + 1
                pass

            instance.system.ver = instance.ver
            instance.system.save()
            pass
        return

    pass

# ==============================================
# SystemVersionMetadata
# ==============================================
class SystemVersionMetadata(models.Model):

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

    licenses = models.ManyToManyField(
        'License', blank=True,
        related_name='systems_licenses')

    oses = models.ManyToManyField(
        'OperatingSystem', blank=True,
        related_name='systems_oses',
        verbose_name='Operating Systems')

    publications = models.ManyToManyField(
        'Publication', blank=True,
        related_name='systems_publications')

    supported_languages = models.ManyToManyField(
        'ProgrammingLanguage', blank=True,
        related_name='systems_supported',
        verbose_name='Supported Languages')

    written_in = models.ManyToManyField(
        'ProgrammingLanguage', blank=True,
        related_name='systems_written')

    def __str__(self):
        system = self.systemversion_set.first()
        return '{} - {} Meta'.format(system.system.name, system.ver)

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

    def publications_str(self):
        return ', '.join([str(l) for l in self.publications.all()])

    def supported_languages_str(self):
        return ', '.join([str(l) for l in self.supported_languages.all()])

    def written_in_str(self):
        return ', '.join([str(l) for l in self.written_in.all()])

    pass


__all__ = (
    'Feature',
    'FeatureOption',
    'License',
    'OperatingSystem',
    'ProgrammingLanguage',
    'ProjectType',
    'Publication',
    'SuggestedSystem',
    'System',
    'SystemFeature',
    'SystemVersion',
    'SystemACL',
    'SystemRecommendation',
    'SystemVisit',
    'SystemVersionMetadata',
)


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
            pass
        else:
            SystemVersion.objects.filter(system=instance.system).update(is_current=False)
            instance.ver = max_ver + 1
            pass

        instance.system.ver = instance.ver
        instance.system.save()
        pass

    return
