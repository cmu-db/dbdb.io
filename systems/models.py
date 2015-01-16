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
    developer = models.CharField(max_length=64, default="", null=True)
    written_in = models.ManyToManyField(ProgrammingLanguage, related_name='wi+')
    oses = models.ManyToManyField(OperatingSystem, related_name='os+')
    publications = models.ManyToManyField(Publication, related_name='p+')
    project_type = models.CharField(max_length=1, choices=PROJECT_TYPES, default="", null=True)
    start_year = models.IntegerField(default=0, null=True)
    end_year = models.IntegerField(default=0, null=True)
    derived_from = models.ManyToManyField('self', related_name='d+')
    
    # Features
    support_sql = models.BooleanField(default=False)
    description_sql = models.TextField(default = "")
    support_foreignkeys = models.BooleanField(default=False)
    description_foreignkeys = models.TextField(default = "")
    support_serverside = models.BooleanField(default=False)
    description_serverside = models.TextField(default = "")
    support_mapreduce = models.BooleanField(default=False)
    description_mapreduce = models.TextField(default = "")
    support_secondary = models.BooleanField(default=False)
    description_secondary = models.TextField(default = "")
    support_durability = models.BooleanField(default=False)
    description_durability = models.TextField(default = "")
    support_triggers = models.BooleanField(default=False)
    description_triggers = models.TextField(default = "")
    support_concurrency = models.BooleanField(default=False)
    description_concurrency = models.TextField(default = "")
    support_languages = models.ManyToManyField(ProgrammingLanguage, related_name='+l')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    # authentication key for editing
    secret_key = models.CharField(max_length = 100, default = None)
    
    def __unicode__(self):
        return self.name
# CLASS