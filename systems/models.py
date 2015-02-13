from django.db import models

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
    year = models.IntegerField()

class System(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(default = "")
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
    
    # Features
    support_sql = models.NullBooleanField()
    description_sql = models.TextField(blank=True, null=True)
    support_foreignkeys = models.NullBooleanField()
    description_foreignkeys = models.TextField(blank=True, null=True)
    support_serverside = models.NullBooleanField()
    description_serverside = models.TextField(blank=True, null=True)
    support_mapreduce = models.NullBooleanField()
    description_mapreduce = models.TextField(blank=True, null=True)
    support_secondary = models.NullBooleanField()
    description_secondary = models.TextField(blank=True, null=True)
    support_durability = models.NullBooleanField()
    description_durability = models.TextField(blank=True, null=True)
    support_triggers = models.NullBooleanField()
    description_triggers = models.TextField(blank=True, null=True)
    support_concurrency = models.NullBooleanField()
    description_concurrency = models.TextField(blank=True, null=True)
    support_datascheme = models.NullBooleanField()
    description_datascheme = models.TextField(blank=True, null=True)
    support_xml = models.NullBooleanField()
    description_xml = models.TextField(blank=True, null=True)
    support_typing = models.NullBooleanField()
    description_typing = models.TextField(blank=True, null=True)
    support_userconcepts = models.NullBooleanField()
    description_userconcepts = models.TextField(blank=True, null=True)
    support_transactionconcepts = models.NullBooleanField()
    description_transactionconcepts = models.TextField(blank=True, null=True)
    support_languages = models.ManyToManyField(ProgrammingLanguage, related_name='systems_supported')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    # authentication key for editing
    secret_key = models.CharField(max_length = 100, default = None)

    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now_add=True, auto_now=True, null=True, blank=True)
    
    def __unicode__(self):
        return self.name
# CLASS