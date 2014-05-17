from django.db import models

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

class Publication(models.Model):
    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=255)
    bibtex = models.TextField(default=None, null=True)
    download = models.URLField(default=None, null=True)
    year = models.IntegerField()
# CLASS

class System(models.Model):
    COMMERCIAL_STATUS_TYPE = (
        ('C', 'Commercial'),
        ('A', 'Academic'),
        ('M', 'Mixed'),
    )
    
    name = models.CharField(max_length=64)
    description = models.TextField()
    website = models.URLField(default=None, null=True)
    written_in = models.ManyToManyField(ProgrammingLanguage, related_name='wi+')
    oses = models.ManyToManyField(OperatingSystem, related_name='os+')
    publications = models.ManyToManyField(Publication, related_name='p+')
    commercial_status = models.CharField(max_length=1, choices=COMMERCIAL_STATUS_TYPE, default=None, null=True)
    start_year = models.IntegerField(default=None, null=True)
    end_year = models.IntegerField(default=None, null=True)
    
    # Features
    support_sql = models.BooleanField(default=False)
    support_foreignkeys = models.BooleanField(default=False)
    support_serverside = models.BooleanField(default=False)
    support_mapreduce = models.BooleanField(default=False)
    support_secondary = models.BooleanField(default=False)
    support_durability = models.BooleanField(default=False)
    support_triggers = models.BooleanField(default=False)
    support_languages = models.ManyToManyField(ProgrammingLanguage, related_name='+l')
    
    def __unicode__(self):
        return self.name
# CLASS