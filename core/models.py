import uuid

from django.db import models
from django.contrib.auth import get_user_model
from autoslug import AutoSlugField
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse
from easy_thumbnails.fields import ThumbnailerImageField


class CoreModel(models.Model):
    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


class OperatingSystem(CoreModel):
    name = models.CharField(max_length=64)
    website = models.URLField(default="", null=True)
    slug = AutoSlugField(populate_from='name', unique=True)


class ProgrammingLanguage(CoreModel):
    name = models.CharField(max_length=64)
    website = models.URLField(default="", null=True)
    slug = AutoSlugField(populate_from='name', unique=True)


class License(CoreModel):
    name = models.CharField(max_length=32)
    website = models.URLField(default=None, null=True)
    slug = AutoSlugField(populate_from='name', unique=True)


class ProjectType(CoreModel):
    name = models.CharField(max_length=32)
    slug = AutoSlugField(populate_from='name', unique=True)


class Publication(CoreModel):
    title = models.CharField(max_length=255, blank=True)
    authors = models.CharField(max_length=255, blank=True)
    bibtex = models.TextField(default=None, null=True, blank=True)
    link = models.URLField(default=None, null=True, blank=True)
    year = models.IntegerField(default=0, null=True)
    number = models.IntegerField(default=1, null=True)
    cite = models.TextField(default=None, null=True, blank=True)

    def __unicode__(self):
        return self.title


class Feature(CoreModel):
    label = models.CharField(max_length=64, unique=True)
    multivalued = models.NullBooleanField(default=True)

    def __unicode__(self):
        return self.label


class FeatureOption(CoreModel):
    feature = models.ForeignKey('Feature', null=True, blank=True)
    value = models.CharField(max_length=64)

    def __unicode__(self):
        return self.value


class SuggestedSystem(CoreModel):
    name = models.CharField(max_length=64)
    description = models.TextField(default=None, null=True, blank=True)
    email = models.EmailField(max_length=100)
    website = models.URLField(null=True, blank=True)
    approved = models.NullBooleanField()
    secret_key = models.UUIDField(max_length=36, default=uuid.uuid4)


class System(CoreModel):
    name = models.CharField(max_length=64, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    current_version = models.PositiveIntegerField(default=0)
    slug = AutoSlugField(populate_from='name', unique=True)
    secret_key = models.UUIDField(max_length=36, default=uuid.uuid4)
    view_count = models.PositiveIntegerField(default=0, blank=True)

    def get_absolute_url(self):
        return reverse('system', args=[self.slug])

    def __hash__(self):
        return hash((
            self.id,
            self.name,
            self.created,
            self.current_version,
            self.secret_key
        ))

    def current(self):
        return self.systemversion_set.get(is_current=True)


class CitationUrls(CoreModel):
    url = models.URLField()

    def __unicode__(self):
        return self.url


class SystemVersion(CoreModel):
    system = models.ForeignKey(System)
    version_number = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(get_user_model())

    description = models.TextField(default="", blank=True, help_text="This field support Markdown Syntax")
    description_citations = models.ManyToManyField(CitationUrls, related_name='version_descriptions', null=True)
    history = models.TextField(default="", blank=True, help_text="This field support Markdown Syntax")
    history_citations = models.ManyToManyField(CitationUrls, related_name='version_histories', null=True)
    website = models.URLField(default="", null=True, blank=True)
    tech_docs = models.URLField(default="", null=True, blank=True)
    developer = models.CharField(max_length=512, default="", blank=True)
    start_year = models.CharField(max_length=128, default="", blank=True)
    start_year_citations = models.ManyToManyField(CitationUrls, related_name='version_start_years', null=True)
    end_year = models.CharField(max_length=128, default="", blank=True)
    end_year_citations = models.ManyToManyField(CitationUrls, related_name='version_end_years', null=True)
    project_type = models.ManyToManyField(ProjectType, blank=True)
    logo = ThumbnailerImageField(upload_to='logos/', blank=True)
    meta = models.ForeignKey('SystemVersionMetadata', null=True, blank=True)
    comment = models.TextField(default="", blank=True)

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return '{} - {}'.format(self.system.name, self.version_number)

    def __hash__(self):
        return hash((
            self.id,
            self.system,
            self.version_number,
            self.is_current,
            self.created
        ))

    def project_type_str(self):
        return ', '.join([str(l) for l in self.project_type.all()])


class SystemVersionMetadata(CoreModel):
    written_in = models.ManyToManyField(ProgrammingLanguage, related_name='systems_written', blank=True)
    supported_languages = models.ManyToManyField(ProgrammingLanguage, related_name='systems_supported', blank=True)
    oses = models.ManyToManyField(OperatingSystem, related_name='systems_oses', blank=True)
    licenses = models.ManyToManyField(License, related_name="systems_licenses", blank=True)
    derived_from = models.TextField(default="", null=True, blank=True)
    publications = models.ManyToManyField(Publication, related_name='systems_publications', blank=True)

    def __unicode__(self):
        system = self.systemversion_set.first()
        return '{} - {} Meta'.format(system.system.name, system.version_number)

    def written_in_str(self):
        return ', '.join([str(l) for l in self.written_in.all()])

    def supported_languages_str(self):
        return ', '.join([str(l) for l in self.supported_languages.all()])

    def oses_str(self):
        return ', '.join([str(l) for l in self.oses.all()])

    def licenses_str(self):
        return ', '.join([str(l) for l in self.licenses.all()])

    def publications_str(self):
        return ', '.join([str(l) for l in self.publications.all()])


class SystemFeatures(CoreModel):
    system = models.ForeignKey(SystemVersion, null=True)
    feature = models.ForeignKey(Feature, null=True)
    value = models.ManyToManyField(FeatureOption, null=True)
    description = models.TextField(help_text='This field supports Markdown Syntax')
    citation = models.ManyToManyField(CitationUrls, null=True)

    def __unicode__(self):
        return self.system.system.name

    def values_str(self):
        return ', '.join([str(l) for l in self.value.all()])


__all__ = (
    'OperatingSystem',
    'ProgrammingLanguage',
    'License',
    'ProjectType',
    'Publication',
    'Feature',
    'FeatureOption',
    'SuggestedSystem',
    'System',
    'SystemVersion',
    'SystemVersionMetadata',
    'SystemFeatures'
)


@receiver(post_save, sender=SystemVersion)
def fix_systemversio_data(sender, instance, created, **kwargs):
    if created:
        last = SystemVersion.objects.filter(system=instance.system).last()
        SystemVersion.objects.filter(system=instance.system).update(is_current=False)
        if last is not None:
            instance.version_number = last.version_number + 1
        instance.system.current_version = instance.version_number
        instance.system.save()
        instance.save()