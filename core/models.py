import uuid

from django.db import models
from django.contrib.auth import get_user_model
from autoslug import AutoSlugField
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

    def get_absolute_url(self):
        return "/system/{}/".format(self.id)


class SystemVersion(CoreModel):
    system = models.ForeignKey(System)
    version_number = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(get_user_model())
    version_message = models.CharField(max_length=500, default="", null=True, blank=True)

    description = models.TextField(default="", blank=True)
    history = models.TextField(default="", blank=True)
    website = models.URLField(default="", null=True, blank=True)
    tech_docs = models.URLField(default="", null=True, blank=True)
    developer = models.CharField(max_length=512, default="", blank=True)
    start_year = models.CharField(max_length=128, default="", blank=True)
    end_year = models.CharField(max_length=128, default="", blank=True)
    project_type = models.ManyToManyField(ProjectType, blank=True)
    logo = ThumbnailerImageField(upload_to='logos/', blank=True)
    meta = models.ForeignKey('SystemVersionMetadata', null=True, blank=True)

    def __unicode__(self):
        return '{} - {}'.format(self.system.name, self.version_number)


class SystemVersionMetadata(CoreModel):
    written_in = models.ManyToManyField(ProgrammingLanguage, related_name='systems_written', blank=True)
    supported_languages = models.ManyToManyField(ProgrammingLanguage, related_name='systems_supported', blank=True)
    oses = models.ManyToManyField(OperatingSystem, related_name='systems_oses', blank=True)
    licenses = models.ManyToManyField(License, related_name="systems_licenses", blank=True)
    derived_from = models.ManyToManyField(System, related_name='systems_derived', blank=True)
    publications = models.ManyToManyField(Publication, related_name='systems_publications', blank=True)

    def __unicode__(self):
        system = self.systemversion_set.first()
        return '{} - {} Meta'.format(system.system.name, system.version_number)


class SystemFeatures(CoreModel):
    system = models.ForeignKey(SystemVersion, null=True)
    feature = models.ForeignKey(Feature, null=True)
    value = models.ManyToManyField(FeatureOption, null=True)

    def __unicode__(self):
        return self.system.name


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
