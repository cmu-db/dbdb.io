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
    feature_sql = models.ForeignKey('Feature', related_name='feature_sql', null=True, blank=True)
    def get_feature_sql(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_sql)

    support_foreignkeys = models.NullBooleanField()
    feature_foreignkeys = models.ForeignKey('Feature', related_name='feature_foreignkeys', null=True, blank=True)
    def get_feature_foreignkeys(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_foreignkeys)

    support_serverside = models.NullBooleanField()
    feature_serverside = models.ForeignKey('Feature', related_name='feature_serverside', null=True, blank=True)
    def get_feature_serverside(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_serverside)

    support_mapreduce = models.NullBooleanField()
    feature_mapreduce = models.ForeignKey('Feature', related_name='feature_mapreduce', null=True, blank=True)
    def get_feature_mapreduce(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_mapreduce)

    support_secondary = models.NullBooleanField()
    feature_secondary = models.ForeignKey('Feature', related_name='feature_secondary', null=True, blank=True)
    def get_feature_secondary(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_secondary)

    support_durability = models.NullBooleanField()
    feature_durability = models.ForeignKey('Feature', related_name='feature_durability', null=True, blank=True)
    def get_feature_durability(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_durability)

    support_triggers = models.NullBooleanField()
    feature_triggers = models.ForeignKey('Feature', related_name='feature_triggers', null=True, blank=True)
    def get_feature_triggers(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_triggers)

    support_concurrency = models.NullBooleanField()
    feature_concurrency = models.ForeignKey('Feature', related_name='feature_concurrency', null=True, blank=True)
    def get_feature_concurrency(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_concurrency)

    support_userconcepts = models.NullBooleanField()
    feature_userconcepts = models.ForeignKey('Feature', related_name='feature_userconcepts', null=True, blank=True)
    def get_feature_userconcepts(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_userconcepts)

    support_datascheme = models.NullBooleanField()
    feature_datascheme = models.ForeignKey('Feature', related_name='feature_datascheme', null=True, blank=True)
    def get_feature_datascheme(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_datascheme)

    support_xml = models.NullBooleanField()
    feature_xml = models.ForeignKey('Feature', related_name='feature_xml', null=True, blank=True)
    def get_feature_xml(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_xml)

    support_typing = models.NullBooleanField()
    feature_typing = models.ForeignKey('Feature', related_name='feature_typing', null=True, blank=True)
    def get_feature_typing(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_typing)

    support_transactionconcepts = models.NullBooleanField()
    feature_transactionconcepts = models.ForeignKey('Feature', related_name='feature_transactionconcepts', null=True, blank=True)
    def get_feature_transactionconcepts(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_transactionconcepts)

    support_querycompilation = models.NullBooleanField()
    feature_querycompilation = models.ForeignKey('Feature', related_name='feature_querycompilation', null=True, blank=True)
    def get_feature_querycompilation(self, *args, **kwargs):
        return FeatureOption.objects.filter(system_version=self,feature=self.feature_querycompilation)

    # Support languages and isolation levels
    support_languages = models.ManyToManyField('ProgrammingLanguage', related_name='systems_supported')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)

    def get_features(self, *args, **kwargs):
        features = []
        self_dict = self.__dict__
        for key in self_dict:
            if key.startswith('feature_'):
                label = feature.label
                multivalued = feature.multivalued
                feature_options = FeatureOptions.objects.filter(system_version=self, feature=self_dict[key])
                feature = {
                    'label': label,
                    'multivalued': multivalued,
                    'feature_options': feature_options
                }
                features.append(feature)

        feature.sort(cmp = lambda x,y: cmp(x.label, y.label))
        return features

    def __unicode__(self):
        return self.name

class Feature(models.Model):
    """Feature that describes a certain aspect of the system"""

    # label for this feature
    label = models.CharField(max_length=64)

    # if the feature has multiple options (FeatureOption)
    multivalued = models.NullBooleanField()

    def __unicode__(self):
        return self.label

class FeatureOption(models.Model):
    """Option for a feature"""

    # System version
    system_version = models.ForeignKey('SystemVersion', null=True, blank=True)

    # feature this option is for
    feature = models.ForeignKey('Feature', null=True, blank=True)

    # value of this feature option
    value = models.CharField(max_length=64)

    # description for what the value means
    description = MarkupField(default='', default_markup_type='markdown', null=True)

    def __unicode__(self):
        return self.value

# CLASS
