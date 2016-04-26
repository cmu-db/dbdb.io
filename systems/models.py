from django.db import models
from markupfield.fields import MarkupField
from django.utils.text import slugify
from django.forms.models import model_to_dict

import util
import hashlib, time

PROJECT_TYPES = (
    ('C', 'Commercial'),
    ('A', 'Academic'),
    ('M', 'Mixed'),
)
for x,y in PROJECT_TYPES:
    globals()['PROJECT_TYPE_' + y.upper()] = x

ISOLATION_LEVELS = (
    ('RC', 'Read Committed'),
    ('RR', 'Repeatable Read'),
    ('CS', 'Cursor Stability'),
    ('SI', 'Snapshot Isolation'),
    ('CR', 'Consistent Read'),
    ('S', 'Serializability'),
)

for x,y in ISOLATION_LEVELS:
    globals()['ISOLATION_LEVEL_' + y.upper()] = x

# FEATURE_LABELS = (
#   ('support_systemarchitecture', 'SYSTEM ARCHITECTURE'),
#   ('support_datamodel', 'DATA MODEL'),
#   ('support_storagemodel', 'STORAGE MODEL'),
#   ('support_queryinterface', 'QUERY INTERFACE'),
#   ('support_storagearchitecture', 'STORAGE ARCHITECTURE'),
#   ('support_concurrencycontrol', 'CONCURRENCY CONTROL'),
#   ('support_isolationlevels', 'ISOLATION LEVELS'),
#   ('support_indexes', 'INDEXES'),
#   ('support_foreignkeys', 'FOREIGN KEYS'),
#   ('support_logging', 'LOGGING'),
#   ('support_checkpoints', 'CHECKPOINTS'),
#   ('support_views', 'VIEWS'),
#   ('support_queryexecution', 'QUERY EXECUTION'),
#   ('support_storedprocedures', 'STORED PROCEDURES'),
#   ('support_joins', 'JOINS'),
#   ('support_querycompilation', 'QUERY COMPILATION'),
# )

# ----------------------------------------------------------------------------

def upload_logo_path(self, fn):
    return "logo/%d/%s" % (self.id, fn)

class OperatingSystem(models.Model):
    name = models.CharField(max_length=64)
    website = models.URLField(default="", null=True)
    slug = models.SlugField(max_length=64)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super(OperatingSystem, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

class ProgrammingLanguage(models.Model):
    name = models.CharField(max_length=64)
    website = models.URLField(default="", null=True)
    slug = models.SlugField(max_length=64)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super(ProgrammingLanguage, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

class License(models.Model):
    name = models.CharField(max_length=32)
    website = models.URLField(default=None, null=True)

    def __unicode__(self):
        return self.name

class DBModel(models.Model):
    name = models.CharField(max_length=32)
    website = models.URLField(default=None, null=True)

    def __unicode__(self):
        return self.name

class APIAccessMethods(models.Model):
    name = models.CharField(max_length=32)
    website = models.URLField(default=None, null=True)

    def __unicode__(self):
        return self.name

class Publication(models.Model):
    title = models.CharField(max_length=255, blank=True)
    authors = models.CharField(max_length=255, blank=True)
    bibtex = models.TextField(default=None, null=True, blank=True)
    download = models.URLField(default=None, null=True, blank=True)
    year = models.IntegerField(default=0, null=True)
    number = models.IntegerField(default=1, null=True)
    cite = models.TextField(default=None, null=True, blank=True)

    def __unicode__(self):
        return self.title

class Feature(models.Model):
    """Feature that describes a certain aspect of the system"""

    # label for this feature
    label = models.CharField(max_length=64)

    # multivalued
    multivalued = models.NullBooleanField(default=True)

    def __unicode__(self):
        return self.label

class FeatureOption(models.Model):
    """Option for a feature"""

    # feature this option is for
    feature = models.ForeignKey('Feature', null=True, blank=True)

    # value of this feature option
    value = models.CharField(max_length=64, default='')

    def __unicode__(self):
        return self.value

class SuggestedSystem(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(default=None, null=True, blank=True)
    email = models.CharField(max_length=100)
    website = models.URLField(default="", null=True)
    approved = models.NullBooleanField()
    secret_key = models.CharField(max_length = 100, default = None)

    def save(self, *args, **kwargs):
        if not self.secret_key:
            self.secret_key = util.generateSecretKey()
        super(SuggestedSystem, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

class System(models.Model):
    """Base article for a system that revisions point back to"""

    # basic, persistent information about the system
    name = models.CharField(max_length=64, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    current_version = models.PositiveIntegerField(default=0)
    slug = models.SlugField(max_length=64)

    # authentication key for editing
    secret_key = models.CharField(max_length=100, default=None)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        if not self.secret_key:
            self.secret_key = util.generateSecretKey()
        super(System, self).save(*args, **kwargs)
    ## DEF

    def __unicode__(self):
        return self.name

class SystemVersion(models.Model):
    """SystemVersion are revisions of the system identified by system"""

    # system that this revision points back to
    system = models.ForeignKey(System)

    # version of this revision
    version_number = models.PositiveIntegerField(default=0)

    # when this revision was created
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # who created this revision
    creator = models.CharField(max_length=100, default="unknown")

    # a message that goes along with this revision
    version_message = models.TextField(max_length=500, default="")

    # basic information about the system, subject to change between revisions
    name = models.CharField(max_length=64)
    description = MarkupField(default="", default_markup_type='markdown')
    history = MarkupField(default="", default_markup_type='markdown')
    website = models.URLField(default="", null=True)
    tech_docs = models.URLField(default="", null=True)
    developer = models.CharField(max_length=64, default="", null=True)
    written_in = models.ManyToManyField('ProgrammingLanguage', related_name='systems_written')
    oses = models.ManyToManyField('OperatingSystem', related_name='systems', blank=True)
    publications = models.ManyToManyField('Publication', related_name='systems', blank=True)
    project_type = models.CharField(max_length=1, choices=PROJECT_TYPES, default="", null=True)
    start_year = models.IntegerField(default=0, null=True)
    end_year = models.IntegerField(default=0, null=True)
    derived_from = models.ManyToManyField('self', related_name='derivatives', blank=True)
    logo_img = models.CharField(max_length=200, default=None, null=True)
    dbmodel = models.ManyToManyField('DBModel', related_name="systems", blank=True)
    license = models.ManyToManyField('License', related_name="systems")
    access_methods = models.ManyToManyField('APIAccessMethods', related_name="systems", blank=True)
    logo = models.FileField(upload_to=upload_logo_path, blank=True)

    # Feature support and descriptions
    support_systemarchitecture = models.NullBooleanField()
    description_systemarchitecture = MarkupField(default="", default_markup_type='markdown')

    support_datamodel = models.NullBooleanField()
    description_datamodel = MarkupField(default="", default_markup_type='markdown')

    support_storagemodel = models.NullBooleanField()
    description_storagemodel = MarkupField(default="", default_markup_type='markdown')

    support_queryinterface = models.NullBooleanField()
    description_queryinterface = MarkupField(default="", default_markup_type='markdown')

    support_storagearchitecture = models.NullBooleanField()
    description_storagearchitecture = MarkupField(default="", default_markup_type='markdown')

    support_concurrencycontrol = models.NullBooleanField()
    description_concurrencycontrol = MarkupField(default="", default_markup_type='markdown')

    support_isolationlevels = models.NullBooleanField()
    description_isolationlevels = MarkupField(default="", default_markup_type='markdown')

    support_indexes = models.NullBooleanField()
    description_indexes = MarkupField(default="", default_markup_type='markdown')

    support_foreignkeys = models.NullBooleanField()
    description_foreignkeys = MarkupField(default="", default_markup_type='markdown')

    support_logging = models.NullBooleanField()
    description_logging = MarkupField(default="", default_markup_type='markdown')

    support_checkpoints = models.NullBooleanField()
    description_checkpoints = MarkupField(default="", default_markup_type='markdown')

    support_views = models.NullBooleanField()
    description_views = MarkupField(default="", default_markup_type='markdown')

    support_queryexecution = models.NullBooleanField()
    description_queryexecution = MarkupField(default="", default_markup_type='markdown')

    support_storedprocedures = models.NullBooleanField()
    description_storedprocedures = MarkupField(default="", default_markup_type='markdown')

    support_joins = models.NullBooleanField()
    description_joins = MarkupField(default="", default_markup_type='markdown')

    support_querycompilation = models.NullBooleanField()
    description_querycompilation = MarkupField(default="", default_markup_type='markdown')

    # feature options
    feature_options = models.ManyToManyField('FeatureOption', related_name='feature_options',
                                             through='SystemVersionFeatureOption')

    # Support languages and isolation levels
    support_languages = models.ManyToManyField('ProgrammingLanguage', related_name='systems_supported')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)

    def __init__(self, *args, **kwargs):
        super(SystemVersion, self).__init__(*args, **kwargs)

    def get_features(self):
        features = []
        all_features = Feature.objects.all()
        for feature in all_features:
            label = feature.label
            field = label.lower().replace(' ', '')

            # get support and description field based on field
            is_supported = self.__dict__['support_' + field]
            description = self.__dict__['description_' + field]
            rendered_description = self.__dict__.get('x_description_' + field + '_rendered', None)
            if rendered_description == None:
                rendered_description = self.__dict__['_description_' + field + '_rendered']

            # all feature options for this feature belonging to this version
            feature_options = SystemVersionFeatureOption.objects.filter(system_version=self)
            feature_options = [x.feature_option for x in feature_options]
            feature_options = [x.value for x in feature_options if x.feature == feature]

            # all options for this feature
            all_feature_options = FeatureOption.objects.filter(feature=feature)
            all_feature_options = [x.value for x in all_feature_options]

            feature = {
                'is_supported': is_supported,
                'label': label,
                'description': description,
                'rendered_description': rendered_description,
                'feature_options': feature_options,
                'all_feature_options': all_feature_options,
                'multivalued': feature.multivalued
            }
            features.append(feature)

        features.sort(cmp = lambda x,y: cmp(x['label'], y['label']))
        return features

    def __unicode__(self):
        return self.name + '-' + str(self.version_number)

    def save(self, *args, **kwargs):
        if not self.name and self.system:
            self.name = self.system.name
        if not self.version_number and self.system:
            self.version_number = self.system.current_version + 1
            self.system.current_version = self.version_number
            self.system.save()
        super(SystemVersion, self).save(*args, **kwargs)

class SystemVersionFeatureOption(models.Model):
    """Cross references a system version with a feature option"""
    system_version = models.ForeignKey(SystemVersion)
    feature_option = models.ForeignKey(FeatureOption)

# CLASS
