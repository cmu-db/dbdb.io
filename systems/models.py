from django.db import models
from markupfield.fields import MarkupField

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

def upload_logo_path(self, fn):
    return "logo/%d/%s" % (self.id, fn)

class System(models.Model):

    name = models.CharField(max_length=64)
    description = MarkupField(default="")
    history = MarkupField(default="")
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
    description_sql = MarkupField(default="", default_markup_type='markdown')
    support_foreignkeys = models.NullBooleanField()
    description_foreignkeys = MarkupField(default="", default_markup_type='markdown')
    support_serverside = models.NullBooleanField()
    description_serverside = MarkupField(default="", default_markup_type='markdown')
    support_mapreduce = models.NullBooleanField()
    description_mapreduce = MarkupField(default="", default_markup_type='markdown')
    support_secondary = models.NullBooleanField()
    description_secondary = MarkupField(default="", default_markup_type='markdown')
    support_durability = models.NullBooleanField()
    description_durability = MarkupField(default="", default_markup_type='markdown')
    support_triggers = models.NullBooleanField()
    description_triggers = MarkupField(default="", default_markup_type='markdown')
    support_concurrency = models.NullBooleanField()
    description_concurrency = MarkupField(default="", default_markup_type='markdown')
    support_datascheme = models.NullBooleanField()
    description_datascheme = MarkupField(default="", default_markup_type='markdown')
    support_xml = models.NullBooleanField()
    description_xml = MarkupField(default="", default_markup_type='markdown')
    support_typing = models.NullBooleanField()
    description_typing = MarkupField(default="", default_markup_type='markdown')
    support_userconcepts = models.NullBooleanField()
    description_userconcepts = MarkupField(default="", default_markup_type='markdown')
    support_transactionconcepts = models.NullBooleanField()
    description_transactionconcepts = MarkupField(default="", default_markup_type='markdown')
    support_querycompilation = models.NullBooleanField()
    description_querycompilation = MarkupField(default="", default_markup_type='markdown')
    support_languages = models.ManyToManyField(ProgrammingLanguage, related_name='systems_supported')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    # authentication key for editing
    secret_key = models.CharField(max_length = 100, default = None)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    version = models.IntegerField(default=0)
    creator = models.CharField(max_length=100, default="unknown")
    version_message = models.TextField(max_length=500, default="")
    
    def __unicode__(self):
        return self.name

class SystemManager(models.Model):
    name = models.CharField(max_length=64)
    current_version = models.ManyToManyField(System, related_name='manager')
    version_number = models.IntegerField(default=0)
    max_version = models.IntegerField(default=0)

    def __unicode__(self):
        return self.name + " Manager" 

# CLASS

