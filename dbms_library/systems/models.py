from django.db import models

class OperatingSystem(models.Model):
    name = models.CharField(max_length=16)
    website = models.URLField(default=None)

class ProgrammingLanguage(models.Model):
    name = models.CharField(max_length=32)
    website = models.URLField(default=None)


class System(models.Model):
    COMMERCIAL_STATUS_TYPE = (
        ('C', 'Commercial'),
        ('A', 'Academic'),
        ('M', 'Mixed'),
    )
    
    name = models.CharField(max_length=64)
    description = models.TextField()
    website = models.URLField(default=None)
    written_in = models.ManyToManyField(ProgrammingLanguage, related_name='wi+')
    oses = models.ManyToManyField(OperatingSystem, related_name='os+')
    commercial_status = models.CharField(max_length=1, choices=COMMERCIAL_STATUS_TYPE, default=None)
    start_year = models.IntegerField(default=None)
    end_year = models.IntegerField(default=None)
    
    # Features
    support_sql = models.BooleanField(default=False)
    support_foreignkeys = models.BooleanField(default=False)
    support_serverside = models.BooleanField(default=False)
    support_mapreduce = models.BooleanField(default=False)
    support_secondary = models.BooleanField(default=False)
    support_durability = models.BooleanField(default=False)
    support_triggers = models.BooleanField(default=False)
    support_languages = models.ManyToManyField(ProgrammingLanguage, related_name='+l')
    