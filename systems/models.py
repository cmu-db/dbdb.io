from django.db import models
from markupfield.fields import MarkupField
from django.utils.text import slugify
from django.forms.models import model_to_dict

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

FEATURE_LABELS = (
    ('SQL', 'SQL'),
    ('FOREIGN KEYS', 'FOREIGN KEYS'),
    ('SERVER SIDE', 'SERVER SIDE'),
    ('MAPREDUCE', 'MAPREDUCE'),
    ('SECONDARY INDEXES', 'SECONDARY INDEXES'),
    ('DURABILITY', 'DURABILITY'),
    ('TRIGGERS', 'TRIGGERS'),
    ('CONCURRENCY', 'CONCURRENCY'),
    ('USER CONCEPTS', 'USER CONCEPTS'),
    ('DATA SCHEME', 'DATA SCHEME'),
    ('XML', 'XML'),
    ('TYPING', 'TYPING'),
    ('TRANSACTION CONCEPTS', 'TRANSACTION CONCEPTS'),
    ('QUERY COMPILATION', 'QUERY COMPILATION'),
)

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

class SuggestedSystem(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(default=None, null=True, blank=True)
    email = models.CharField(max_length=100)
    website = models.URLField(default="", null=True)
    approved = models.NullBooleanField()
    secret_key = models.CharField(max_length = 100, default = None)

    def save(self, *args, **kwargs):
        if not self.secret_key:
            key = hashlib.sha1()
            key.update(str(time.time()))
            self.secret_key = key.hexdigest()[:11]
        super(SuggestedSystem, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

class System(models.Model):
    """Base article for a system that revisions point back to"""

    # basic, persistent information about the system
    name = models.CharField(max_length=64, null=False)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    current_version = models.IntegerField(default=0)
    slug = models.SlugField(max_length=64)

    # authentication key for editing
    secret_key = models.CharField(max_length = 100, default = None)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        if not self.secret_key:
            key = hashlib.sha1()
            key.update(str(time.time()))
            self.secret_key = key.hexdigest()[:11]
        super(System, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

class SystemVersion(models.Model):
    """SystemVersion are revisions of the system identified by system"""

    # system that this revision points back to
    system = models.ForeignKey(System)

    # version of this revision
    version_number = models.IntegerField(default=0)

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

    # Features
    support_concurrency = models.NullBooleanField()
    feature_concurrency = models.ForeignKey('Feature', related_name='feature_concurrency', default=1)

    support_datascheme = models.NullBooleanField()
    feature_datascheme = models.ForeignKey('Feature', related_name='feature_datascheme', default=2)

    support_durability = models.NullBooleanField()
    feature_durability = models.ForeignKey('Feature', related_name='feature_durability', default=3)

    support_foreignkeys = models.NullBooleanField()
    feature_foreignkeys = models.ForeignKey('Feature', related_name='feature_foreignkeys', default=4)

    support_mapreduce = models.NullBooleanField()
    feature_mapreduce = models.ForeignKey('Feature', related_name='feature_mapreduce', default=5)

    support_querycompilation = models.NullBooleanField()
    feature_querycompilation = models.ForeignKey('Feature', related_name='feature_querycompilation', default=6)

    support_secondaryindexes = models.NullBooleanField()
    feature_secondaryindexes = models.ForeignKey('Feature', related_name='feature_secondaryindexes', default=7)

    support_serverside = models.NullBooleanField()
    feature_serverside = models.ForeignKey('Feature', related_name='feature_serverside', default=8)

    support_sql = models.NullBooleanField()
    feature_sql = models.ForeignKey('Feature', related_name='feature_sql', default=9)

    support_transactionconcepts = models.NullBooleanField()
    feature_transactionconcepts = models.ForeignKey('Feature', related_name='feature_transactionconcepts', default=10)

    support_triggers = models.NullBooleanField()
    feature_triggers = models.ForeignKey('Feature', related_name='feature_triggers', default=11)

    support_typing = models.NullBooleanField()
    feature_typing = models.ForeignKey('Feature', related_name='feature_typing', default=12)

    support_userconcepts = models.NullBooleanField()
    feature_userconcepts = models.ForeignKey('Feature', related_name='feature_userconcepts', default=13)

    support_xml = models.NullBooleanField()
    feature_xml = models.ForeignKey('Feature', related_name='feature_xml', default=14)

    # Support languages and isolation levels
    support_languages = models.ManyToManyField('ProgrammingLanguage', related_name='systems_supported')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)

    def get_features(self, *args, **kwargs):
        features = []
        for key in self.__dict__:
            if key.startswith('feature_'):
                feature = Feature.objects.get(id=self.__dict__[key])
                label = feature.label
                description = feature.description
                rendered_description = feature.get_description_rendered()

                # get a list of all feature options already selected for this feature
                feature_options = FeatureOption.objects.filter(feature=feature)
                feature_options = [x.value for x in feature_options if x.feature.system_version == self]

                # get all feature options, then create a list based on just the labels that match
                all_feature_options = FeatureOption.objects.all()
                all_feature_options = [x.value for x in all_feature_options if x.feature.label == label
                                        and not x.feature.system_version]

                feature = {
                    'is_supported': self.__dict__[key.replace('feature','support').replace('_id','')],
                    'label': label,
                    'description': description,
                    'rendered_description': rendered_description,
                    'feature_options': feature_options,
                    'all_feature_options': all_feature_options,
                    'multivalued': feature.multivalued,
                    'options_size': len(all_feature_options)
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

class Feature(models.Model):
    """Feature that describes a certain aspect of the system"""

    # label for this feature
    label = models.CharField(max_length=64, choices=FEATURE_LABELS)

    # multivalued
    multivalued = models.NullBooleanField(default=True)

    # System version
    system_version = models.ForeignKey('SystemVersion', null=True, blank=True)

    # description for the selected feature options
    description = MarkupField(default='', default_markup_type='markdown', null=True)

    # https://github.com/jamesturk/django-markupfield#usage
    def get_description_rendered(self, *args, **kwargs):
        return self.__dict__['_description_rendered']

    def __unicode__(self):
        return self.label + '-' + str(self.system_version)

class FeatureOption(models.Model):
    """Option for a feature"""

    # feature this option is for
    feature = models.ForeignKey('Feature', null=True, blank=True)

    # value of this feature option
    value = models.CharField(max_length=64, default='foo')

    def __unicode__(self):
        return self.value

# CLASS
