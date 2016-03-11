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

for x,y in ISOLATION_LEVELS:
    globals()['ISOLATION_LEVEL_' + y.upper()] = x

# ----------------------------------------------------------------------------

def upload_logo_path(self, fn):
    return "logo/%d/%s" % (self.id, fn)

class OperatingSystem(models.Model):
    name = models.CharField(max_length=64)
    website = models.URLField(default="", null=True)
    slug = models.SlugField(max_length=64)

    def save(self, *args, **kwargs):
        if not self.id:
            # Only generate the slug when the object is created
            self.slug = slugify(self.name)

    def __unicode__(self):
        return self.name

class ProgrammingLanguage(models.Model):
    name = models.CharField(max_length=64)
    website = models.URLField(default="", null=True)
    slug = models.SlugField(max_length=64)

    def save(self, *args, **kwargs):
        if not self.id:
            # Only generate the slug when the object is created
            self.slug = slugify(self.name)

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
    slug = models.SlugField(max_length=64)

    def save(self, *args, **kwargs):
        if not self.id:
            # Only generate the slug when the object is created
            self.slug = slugify(self.name)

        super(System, self).save(*args, **kwargs)

    # authentication key for editing
    secret_key = models.CharField(max_length = 100, default = None)
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
    support_sql = models.NullBooleanField()
    description_sql = models.ForeignKey('Feature', related_name='description_sql', null=True, blank=True)
    def get_description_sql(self):
        return 'Hi!'
        # if self.description_sql is not None:
        #     return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_foreignkeys = models.NullBooleanField()
    description_foreignkeys = models.ForeignKey('Feature', related_name='description_foreignkeys', null=True, blank=True)
    def get_description_foreignkeys(self, *args, **kwargs):
        if self.description_foreignkeys is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_foreignkeys)

    support_serverside = models.NullBooleanField()
    description_serverside = models.ForeignKey('Feature', related_name='description_serverside', null=True, blank=True)
    def get_description_serverside(self, *args, **kwargs):
        if self.description_serverside is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_serverside)

    support_mapreduce = models.NullBooleanField()
    description_mapreduce = models.ForeignKey('Feature', related_name='description_mapreduce', null=True, blank=True)
    def get_description_mapreduce(self, *args, **kwargs):
        if self.description_mapreduce is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_mapreduce)

    support_secondary = models.NullBooleanField()
    description_secondary = models.ForeignKey('Feature', related_name='description_secondary', null=True, blank=True)
    def get_description_secondary(self, *args, **kwargs):
        if self.description_secondary is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_secondary)

    support_durability = models.NullBooleanField()
    description_durability = models.ForeignKey('Feature', related_name='description_durability', null=True, blank=True)
    def get_description_durability(self, *args, **kwargs):
        if self.description_durability is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_durability)

    support_triggers = models.NullBooleanField()
    description_triggers = models.ForeignKey('Feature', related_name='description_triggers', null=True, blank=True)
    def get_description_triggers(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_concurrency = models.NullBooleanField()
    description_concurrency = models.ForeignKey('Feature', related_name='description_concurrency', null=True, blank=True)
    def get_description_concurrency(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_userconcepts = models.NullBooleanField()
    description_userconcepts = models.ForeignKey('Feature', related_name='description_userconcepts', null=True, blank=True)
    def get_description_userconcepts(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_datascheme = models.NullBooleanField()
    description_datascheme = models.ForeignKey('Feature', related_name='description_datascheme', null=True, blank=True)
    def get_description_datascheme(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_xml = models.NullBooleanField()
    description_xml = models.ForeignKey('Feature', related_name='description_xml', null=True, blank=True)
    def get_description_xml(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_typing = models.NullBooleanField()
    description_typing = models.ForeignKey('Feature', related_name='description_typing', null=True, blank=True)
    def get_description_typing(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_transactionconcepts = models.NullBooleanField()
    description_transactionconcepts = models.ForeignKey('Feature', related_name='description_transactionconcepts', null=True, blank=True)
    def get_description_transactionconcepts(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    support_querycompilation = models.NullBooleanField()
    description_querycompilation = models.ForeignKey('Feature', related_name='description_querycompilation', null=True, blank=True)
    def get_description_querycompilation(self, *args, **kwargs):
        if self.description_sql is not None:
            return FeatureOption.objects.filter(system_version=self,feature=self.description_sql)

    # Support languages and isolation levels
    support_languages = models.ManyToManyField('ProgrammingLanguage', related_name='systems_supported')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)

    def __unicode__(self):
        return self.name

class Feature(models.Model):
    """Feature that describes a certain aspect of the system"""

    # what the field is or its 'label'
    field = models.CharField(max_length=64)

    # if the feature has multiple options (FeatureOption)
    multivalued = models.NullBooleanField()

    def __unicode__(self):
        return self.field

class FeatureOption(models.Model):
    """Option for a feature"""

    # System version
    system_version = models.ForeignKey('SystemVersion', null=True, blank=True)

    # feature this option is for
    feature = models.ForeignKey('Feature', null=True, blank=True)

    # description for what the option means
    description = MarkupField(default='', default_markup_type='markdown', null=True)

    def get_description(self, *args, **kwargs):
        return self.description

    def __unicode__(self):
        return self.feature.field

# CLASS
