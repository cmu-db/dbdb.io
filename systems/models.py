from django.db import models
from markupfield.fields import MarkupField
from django.utils.text import slugify

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

default_slug = slugify("foo")
for x,y in ISOLATION_LEVELS:
    globals()['ISOLATION_LEVEL_' + y.upper()] = x


# ----------------------------------------------------------------------------

def upload_logo_path(self, fn):
    return "logo/%d/%s" % (self.id, fn)

class OperatingSystem(models.Model):
    name = models.CharField(max_length=16)
    website = models.URLField(default="", null=True)
    def __unicode__(self):
        return self.name

class ProgrammingLanguage(models.Model):
    name = models.CharField(max_length=32)
    website = models.URLField(default="", null=True)
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
    def __unicode__(self):
        return self.name

class System(models.Model):
    """Base article for a system that revisions point back to"""

    # basic, persistent information about the system
    name = models.CharField(max_length=64, null=False)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    current_version = models.IntegerField(default=0)
    creator = models.CharField(max_length=100, default="unknown")
    slug = models.SlugField(max_length=50)

    # authentication key for editing
    secret_key = models.CharField(max_length = 100, default = None)

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
    written_in = models.ManyToManyField(ProgrammingLanguage, related_name='systems_written')
    oses = models.ManyToManyField(OperatingSystem, related_name='systems')
    publications = models.ManyToManyField(Publication, related_name='systems')
    project_type = models.CharField(max_length=1, choices=PROJECT_TYPES, default="", null=True)
    start_year = models.IntegerField(default=0, null=True)
    end_year = models.IntegerField(default=0, null=True)
    derived_from = models.ManyToManyField('self', related_name='derivatives')
    logo_img = models.CharField(max_length=200, default=None, null=True)
    dbmodel = models.ManyToManyField(DBModel, related_name="systems")
    license = models.ManyToManyField(License, related_name="systems")
    access_methods = models.ManyToManyField(APIAccessMethods, related_name="systems")
    logo = models.FileField(upload_to=upload_logo_path)

    # Features
    support_sql = models.NullBooleanField()
    description_sql = models.ForeignKey('FeatureOption', related_name='description_sql', null=True, blank=True)

    support_foreignkeys = models.NullBooleanField()
    description_foreignkeys = models.ForeignKey('FeatureOption', related_name='description_foreignkeys', null=True, blank=True)

    support_serverside = models.NullBooleanField()
    description_serverside = models.ForeignKey('FeatureOption', related_name='description_serverside', null=True, blank=True)

    support_mapreduce = models.NullBooleanField()
    description_mapreduce = models.ForeignKey('FeatureOption', related_name='description_mapreduce', null=True, blank=True)

    support_secondary = models.NullBooleanField()
    description_secondary = models.ForeignKey('FeatureOption', related_name='description_secondary', null=True, blank=True)

    support_durability = models.NullBooleanField()
    description_durability = models.ForeignKey('FeatureOption', related_name='description_durability', null=True, blank=True)

    support_triggers = models.NullBooleanField()
    description_triggers = models.ForeignKey('FeatureOption', related_name='description_triggers', null=True, blank=True)

    support_concurrency = models.NullBooleanField()
    description_concurrency = models.ForeignKey('FeatureOption', related_name='description_concurrency', null=True, blank=True)

    support_datascheme = models.NullBooleanField()
    description_datascheme = models.ForeignKey('FeatureOption', related_name='description_datascheme', null=True, blank=True)

    support_xml = models.NullBooleanField()
    description_xml = models.ForeignKey('FeatureOption', related_name='description_xml', null=True, blank=True)

    support_typing = models.NullBooleanField()
    description_typing = models.ForeignKey('FeatureOption', related_name='description_typing', null=True, blank=True)

    support_userconcepts = models.NullBooleanField()
    description_userconcepts = models.ForeignKey('FeatureOption', related_name='description_userconcepts', null=True, blank=True)

    support_transactionconcepts = models.NullBooleanField()
    description_transactionconcepts = models.ForeignKey('FeatureOption', related_name='description_transactionconcepts', null=True, blank=True)

    support_querycompilation = models.NullBooleanField()
    description_querycompilation = models.ForeignKey('FeatureOption', related_name='description_querycompilation', null=True, blank=True)

    # Support languages and isolation levels
    support_languages = models.ManyToManyField(ProgrammingLanguage, related_name='systems_supported')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)

    def __unicode__(self):
        return self.name

class Feature(models.Model):
    """Feature that describes a certain aspect of the system"""

    # what the field is or its 'label'
    field = models.CharField(max_length=64, default='')

    # if the feature has multiple options (FeatureOption)
    multivalued = models.NullBooleanField()

class FeatureOption(models.Model):
    """Option for a feature"""

    # feature this option is for
    feature = models.ForeignKey('Feature', null=True, blank=True)

    # what this option actually is
    value = MarkupField(default='', default_markup_type='markdown', null=True)

    # description for what the option means
    description = models.TextField(max_length=500, default="")

# CLASS
