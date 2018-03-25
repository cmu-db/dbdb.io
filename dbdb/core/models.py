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


# concrete models

class CitationUrl(models.Model):

    url = models.URLField(max_length=500)

    def __str__(self):
        return self.url

    pass

class Feature(models.Model):

    label = models.CharField(max_length=100, unique=True)
    multivalued = models.BooleanField(default=True)

    class Meta:
        ordering = ('label',)

    def __str__(self):
        return self.label

    pass

class FeatureOption(models.Model):

    feature = models.ForeignKey('Feature', models.CASCADE)

    value = models.CharField(max_length=100)

    def __str__(self):
        return self.value

    pass

class License(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=32)
    website = models.URLField(blank=True, max_length=512)

    class Meta:
        ordering = ('name',)


    def __str__(self):
        return self.name

    pass

class OperatingSystem(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    url = models.URLField(blank=True, max_length=500)

    class Meta:
        ordering = ('name',)


    def __str__(self):
        return self.name

    pass

class ProgrammingLanguage(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    url = models.URLField(blank=True, max_length=500)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    pass

class ProjectType(models.Model):

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=32)

    class Meta:
        ordering = ('name',)


    def __str__(self):
        return self.name

    pass

class Publication(models.Model):

    title = models.CharField(max_length=250)
    authors = models.CharField(blank=True, max_length=250)
    year = models.PositiveIntegerField(blank=True, null=True)
    number = models.IntegerField(default=1, null=True)
    url = models.URLField(blank=True, max_length=500)

    bibtex = models.TextField(default=None, null=True, blank=True)
    cite = models.TextField(default=None, null=True, blank=True)

    def __str__(self):
        return self.title

    pass

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
        return self.systemversion_set.get(is_current=True)

    def get_absolute_url(self):
        return reverse('system', args=[self.slug])

    pass

class SystemFeature(models.Model):

    system = models.ForeignKey('SystemVersion', models.CASCADE, related_name='features')
    feature = models.ForeignKey('Feature', models.CASCADE)

    citations = models.ManyToManyField('CitationUrl')
    options = models.ManyToManyField('FeatureOption')

    description = models.TextField(blank=True, help_text='This field supports Markdown Syntax')

    class Meta:
        unique_together = ('system','feature')

    def __str__(self):
        return self.system.system.name

    def values_str(self):
        return ', '.join([str(l) for l in self.options.all()])

    pass

class SystemVersion(models.Model):

    system = models.ForeignKey('System', models.CASCADE)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    meta = models.ForeignKey('SystemVersionMetadata', models.SET_NULL, blank=True, null=True)

    description_citations = models.ManyToManyField('CitationUrl', blank=True, related_name='version_descriptions')
    end_year_citations = models.ManyToManyField('CitationUrl', blank=True, related_name='version_end_years')
    history_citations = models.ManyToManyField('CitationUrl', blank=True, related_name='version_histories')
    project_types = models.ManyToManyField('ProjectType', blank=True, related_name='project_types', verbose_name='Project Type')
    start_year_citations = models.ManyToManyField('CitationUrl', blank=True, related_name='version_start_years')

    created = models.DateTimeField(default=timezone.now)
    is_current = models.BooleanField(default=True)
    developer = models.CharField(blank=True, max_length=500)
    start_year = models.PositiveIntegerField(blank=True, null=True)
    end_year = models.PositiveIntegerField(blank=True, null=True)
    logo = ThumbnailerImageField(blank=True, upload_to='logos/')
    tech_docs = models.URLField(blank=True, max_length=500)
    url = models.URLField(blank=True, max_length=500)
    ver = models.PositiveIntegerField('Version No.', default=1)

    description = models.TextField(blank=True, help_text="This field support Markdown Syntax")
    history = models.TextField(blank=True, help_text="This field support Markdown Syntax")
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ('-ver',)
        unique_together = ('system','ver')

    def __hash__(self):
        return hash((
            self.created,
            self.id,
            self.is_current,
            self.system,
            self.ver,
        ))

    def __str__(self):
        return '{} - {}'.format(self.system.name, self.ver)

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

class SystemVersionMetadata(models.Model):

    derived_from = models.ManyToManyField('System', blank=True, related_name='derived_from_systems', verbose_name='Systems Derived From')
    licenses = models.ManyToManyField('License', blank=True, related_name='systems_licenses')
    oses = models.ManyToManyField('OperatingSystem', blank=True, related_name='systems_oses', verbose_name='Operating Systems')
    publications = models.ManyToManyField('Publication', blank=True, related_name='systems_publications')
    supported_languages = models.ManyToManyField('ProgrammingLanguage', blank=True, related_name='systems_supported', verbose_name='Supported Languages')
    written_in = models.ManyToManyField('ProgrammingLanguage', blank=True, related_name='systems_written')

    def __str__(self):
        system = self.systemversion_set.first()
        return '{} - {} Meta'.format(system.system.name, system.version_number)

    def derived_from_str(self):
        return ', '.join([str(l) for l in self.derived_from.all()])

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
    print( 'system_id,ver', (instance.system_id, instance.ver) )
    return
