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
    website = models.URLField(default=None, null=True)
    def __unicode__(self):
        return self.name
# CLASS

class ProgrammingLanguage(models.Model):
    name = models.CharField(max_length=32)
    website = models.URLField(default=None, null=True)
    def __unicode__(self):
        return self.name
# CLASS

class License(models.Model):
    name = models.CharField(max_length=32)
    website = models.URLField(default=None, null=True)
    def __unicode__(self):
        return self.name
# CLASS

class ConcurrencyControl(models.Model):
    name = models.CharField(max_length=16)
    description = models.TextField()
    def __unicode__(self):
        return self.name
# CLASS

class Publication(models.Model):
    title = models.CharField(max_length=255, blank=True)
    authors = models.CharField(max_length=255, blank=True)
    bibtex = models.TextField(default=None, null=True, blank=True)
    download = models.URLField(default=None, null=True, blank=True)
    year = models.IntegerField()
# CLASS

class System(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField()
    website = models.URLField(default=None, null=True)
    developer = models.CharField(max_length=64, default=None, null=True)
    written_in = models.ManyToManyField(ProgrammingLanguage, related_name='wi+')
    oses = models.ManyToManyField(OperatingSystem, related_name='os+')
    publications = models.ManyToManyField(Publication, related_name='p+')
    project_type = models.CharField(max_length=1, choices=PROJECT_TYPES, default=None, null=True)
    start_year = models.IntegerField(default=None, null=True)
    end_year = models.IntegerField(default=None, null=True)
    derived_from = models.ManyToManyField('self', related_name='d+')
    
    # Features
    support_sql = models.BooleanField(default=False)
    support_foreignkeys = models.BooleanField(default=False)
    support_serverside = models.BooleanField(default=False)
    support_mapreduce = models.BooleanField(default=False)
    support_secondary = models.BooleanField(default=False)
    support_durability = models.BooleanField(default=False)
    support_triggers = models.BooleanField(default=False)
    support_languages = models.ManyToManyField(ProgrammingLanguage, related_name='+l')
    default_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    max_isolation = models.CharField(max_length=2, choices=ISOLATION_LEVELS, default=None, null=True)
    concurrency = models.ForeignKey(ConcurrencyControl)
    
    def __unicode__(self):
        return self.name
# CLASS