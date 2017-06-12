from django.db import models
from django.db.models import Q
from django.utils.text import slugify

import util


# ----------------------------------------------------------------------------

def get_options(label):
    feature = Feature.objects.filter(label=label)
    return Q(feature=feature)


def upload_logo_orig(instance, filename):
    extension = filename[filename.rfind('.'):]
    filename = instance.system.slug + '-' + str(instance.version_number) + extension
    return 'website/static/images/originals/' + instance.system.slug + '/' + filename


def upload_logo_thumb(instance, filename):
    filename = instance.system.slug + '-' + instance.system.current_version
    return 'website/static/images/thumbnails/' + instance.system.slug + '/' + filename


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
    slug = models.SlugField(max_length=64)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super(License, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name


class ProjectType(models.Model):
    name = models.CharField(max_length=32)
    slug = models.URLField(default=None, null=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super(ProjectType, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name


class Publication(models.Model):
    title = models.CharField(max_length=255, blank=True)
    authors = models.CharField(max_length=255, blank=True)
    bibtex = models.TextField(default=None, null=True, blank=True)
    link = models.URLField(default=None, null=True, blank=True)
    year = models.IntegerField(default=0, null=True)
    number = models.IntegerField(default=1, null=True)
    cite = models.TextField(default=None, null=True, blank=True)

    def __unicode__(self):
        return self.title


class Feature(models.Model):
    """Feature that describes a certain aspect of the system"""

    # label for this feature
    label = models.CharField(max_length=64)

    # multivalued
    multivalued = models.NullBooleanField(default=True)

    def __unicode__(self):
        return self.label


class FeatureOption(models.Model):
    """Option for a feature"""

    # feature this option is for
    feature = models.ForeignKey('Feature', null=True, blank=True)

    # value of this feature option
    value = models.CharField(max_length=64, default='')

    def __unicode__(self):
        return self.value


class SuggestedSystem(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(default=None, null=True, blank=True)
    email = models.CharField(max_length=100)
    website = models.URLField(default="", null=True)
    approved = models.NullBooleanField()
    secret_key = models.CharField(max_length=100, default=None)

    def save(self, *args, **kwargs):
        if not self.secret_key:
            self.secret_key = util.generateSecretKey()
        super(SuggestedSystem, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name


class System(models.Model):
    """Base article for a system that revisions point to"""

    # basic, persistent information about the system
    name = models.CharField(max_length=64, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    current_version = models.PositiveIntegerField(default=1)
    slug = models.SlugField(max_length=64)

    # authentication key for editing
    secret_key = models.CharField(max_length=100, null=True, default=None)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        if not self.secret_key:
            self.secret_key = util.generateSecretKey()
        super(System, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name


class SystemVersion(models.Model):

    """SystemVersion are revisions of the system identified by system"""

    # System that this revision points back to
    system = models.ForeignKey(System)

    # Version of this revision
    version_number = models.PositiveIntegerField(default=1)

    # If this version is the current version
    current = models.BooleanField(default=True)

    # When this revision was created
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # Who created this revision
    creator = models.CharField(max_length=100, default="unknown")

    # A message that goes along with this revision
    version_message = models.CharField(max_length=500, default="", null=True, blank=True)

    # Basic data
    name = models.CharField(max_length=64)
    description = models.TextField(default="", blank=True)
    history = models.TextField(default="", blank=True)
    website = models.URLField(default="", null=True, blank=True)
    tech_docs = models.URLField(default="", null=True, blank=True)
    developer = models.CharField(max_length=512, default="", blank=True)
    start_year = models.CharField(max_length=128, default="", blank=True)
    end_year = models.CharField(max_length=128, default="", blank=True)
    project_type = models.ManyToManyField(ProjectType, blank=True)

    # Logos
    logo_orig = models.ImageField(upload_to=upload_logo_orig, blank=True)
    logo_thumb = models.ImageField(upload_to=upload_logo_thumb, blank=True)

    # Model data
    written_in = models.ManyToManyField('ProgrammingLanguage', related_name='systems_written', blank=True)
    supported_languages = models.ManyToManyField('ProgrammingLanguage', related_name='systems_supported', blank=True)
    oses = models.ManyToManyField('OperatingSystem', related_name='systems_oses', blank=True)
    licenses = models.ManyToManyField('License', related_name="systems_licenses", blank=True)
    derived_from = models.ManyToManyField('System', related_name='systems_derived', blank=True)
    publications = models.ManyToManyField('Publication', related_name='systems_publications', blank=True)

    # Feature support and descriptions
    support_systemarchitecture = models.NullBooleanField()
    options_systemarchitecture = models.ManyToManyField('FeatureOption',
                                                        related_name='options_systemarchitecture',
                                                        blank=True,
                                                        limit_choices_to=get_options('System Architecture'))
    description_systemarchitecture = models.TextField(
        default='Is it a shared-memory, shared-disk, or shared-nothing DBMS? '
                'Does it rely on special hardware (e.g., GPU, FPGA)?', blank=True)

    support_datamodel = models.NullBooleanField()
    options_datamodel = models.ManyToManyField('FeatureOption',
                                               related_name='options_datamodel',
                                               blank=True,
                                               limit_choices_to=get_options('Data Model'))
    description_datamodel = models.TextField(default='What is the primary data model of the DBMS?', blank=True)

    support_storagemodel = models.NullBooleanField()
    options_storagemodel = models.ManyToManyField('FeatureOption',
                                                  related_name='options_storagemodel',
                                                  blank=True,
                                                  limit_choices_to=get_options('Storage Model'))
    description_storagemodel = models.TextField(default='What kind of storage models does the DBMS support '
                                                        '(e.g., NSM, DSM)?', blank=True)

    support_queryinterface = models.NullBooleanField()
    options_queryinterface = models.ManyToManyField('FeatureOption',
                                                    related_name='options_queryinterface',
                                                    blank=True,
                                                    limit_choices_to=get_options('Query Interface'))
    description_queryinterface = models.TextField(
        default='What language or API does the DBMS support for the application '
                'to load data and execute queries.', blank=True)

    support_storagearchitecture = models.NullBooleanField()
    options_storagearchitecture = models.ManyToManyField('FeatureOption',
                                                         related_name='options_storagearchitecture',
                                                         blank=True,
                                                         limit_choices_to=get_options('Storage Architecture'))
    description_storagearchitecture = models.TextField(default='Is the system a disk-oriented or in-memory DBMS? '
                                                               'If the latter, does it support larger-than-memory '
                                                               'databases?', blank=True)

    support_concurrencycontrol = models.NullBooleanField()
    options_concurrencycontrol = models.ManyToManyField('FeatureOption',
                                                        related_name='options_concurrencycontrol',
                                                        blank=True,
                                                        limit_choices_to=get_options('Concurrency Control'))
    description_concurrencycontrol = models.TextField(default='Does the DBMS support transactions and if so what '
                                                              'concurrency control scheme does it use?', blank=True)

    support_isolationlevels = models.NullBooleanField()
    options_isolationlevels = models.ManyToManyField('FeatureOption',
                                                     related_name='options_isolationlevels',
                                                     blank=True,
                                                     limit_choices_to=get_options('Isolation Levels'))
    description_isolationlevels = models.TextField(
        default='What isolation levels does it support? Which one is the default?'
                ' How does it implement each one?', blank=True)

    support_indexes = models.NullBooleanField()
    options_indexes = models.ManyToManyField('FeatureOption',
                                             related_name='options_indexes',
                                             blank=True,
                                             limit_choices_to=get_options('Indexes'))
    description_indexes = models.TextField(default='What kind of indexes does the DBMS support (e.g., primary key, '
                                                   'secondary, derived, partial)? What data structures does the DBMS '
                                                   'support? What is the default?', blank=True)

    support_foreignkeys = models.NullBooleanField()
    options_foreignkeys = models.ManyToManyField('FeatureOption',
                                                 related_name='options_foreignkeys',
                                                 blank=True,
                                                 limit_choices_to=get_options('Foreign Keys'))
    description_foreignkeys = models.TextField(default='Does the system support foreign key constraints?', blank=True)

    support_logging = models.NullBooleanField()
    options_logging = models.ManyToManyField('FeatureOption',
                                             related_name='options_logging',
                                             blank=True,
                                             limit_choices_to=get_options('Logging'))
    description_logging = models.TextField(default='How does the system support data durability? What kind of logging '
                                                   'scheme does it use (e.g., physical, logical, physiological)?',
                                           blank=True)

    support_checkpoints = models.NullBooleanField()
    options_checkpoints = models.ManyToManyField('FeatureOption',
                                                 related_name='options_checkpoints',
                                                 blank=True,
                                                 limit_choices_to=get_options('Checkpoints'))
    description_checkpoints = models.TextField(
        default='How does the DBMS take checkpoints? What kind of checkpoints are '
                'they (e.g., fuzzy vs. non-fuzzy)?', blank=True)

    support_views = models.NullBooleanField()
    options_views = models.ManyToManyField('FeatureOption',
                                           related_name='options_views',
                                           blank=True,
                                           limit_choices_to=get_options('Views'))
    description_views = models.TextField(
        default='Does the DBMS support views or materialized views? How complex of a query'
                ' does it support?', blank=True)

    support_queryexecution = models.NullBooleanField()
    options_queryexecution = models.ManyToManyField('FeatureOption',
                                                    related_name='options_queryexecution',
                                                    blank=True,
                                                    limit_choices_to=get_options('Query Execution'))
    description_queryexecution = models.TextField(
        default='What query processing model does the DBMS support (e.g., iterator'
                ' vs. vectorized)? What kind of intra-query parallelism does it '
                'support?', blank=True)

    support_storedprocedures = models.NullBooleanField()
    options_storedprocedures = models.ManyToManyField('FeatureOption',
                                                      related_name='options_storedprocedures',
                                                      blank=True,
                                                      limit_choices_to=get_options('Stored Procedures'))
    description_storedprocedures = models.TextField(default='Does the DBMS support stored procedures? If so, what '
                                                            'language(s) can they be written in?', blank=True)

    support_joins = models.NullBooleanField()
    options_joins = models.ManyToManyField('FeatureOption',
                                           related_name='options_joins',
                                           blank=True,
                                           limit_choices_to=get_options('Joins'))
    description_joins = models.TextField(
        default='What join algorithms does the DBMS support? What is notable or special'
                ' about them (e.g., low-memory, parallelism)?', blank=True)

    support_querycompilation = models.NullBooleanField()
    options_querycompilation = models.ManyToManyField('FeatureOption',
                                                      related_name='options_querycompilation',
                                                      blank=True,
                                                      limit_choices_to=get_options('Query Compilation'))
    description_querycompilation = models.TextField(
        default='Does the DBMS support code generation or JIT optimizations? '
                'How does it do this (e.g., LLVM, templates, code gen)?', blank=True)

    support_accessmethods = models.NullBooleanField()
    options_accessmethods = models.ManyToManyField('FeatureOption',
                                                   related_name='options_accessmethods',
                                                   blank=True,
                                                   limit_choices_to=get_options('Access Methods'))
    description_accessmethods = models.TextField(default='What API access methods are available for the DBMS?',
                                                 blank=True)

    def get_features(self):
        features = []
        all_features = Feature.objects.all()
        for feature in all_features:
            label = feature.label
            field = label.lower().replace(' ', '')

            # Get if this version supports featue, options, and description
            is_supported = self.__dict__['support_' + field]
            options = self.__getattribute__('options_' + field)
            options = [o.value for o in options.all()]
            description = self.__dict__['description_' + field]

            feature = {
                'is_supported': is_supported,
                'label': label,
                'description': description,
                'feature_options': options,
                'multivalued': feature.multivalued
            }
            features.append(feature)

        features.sort(cmp=lambda x, y: cmp(x['label'], y['label']))
        return features

    def __unicode__(self):
        return self.name + ' - ' + str(self.version_number)

    def save(self, *args, **kwargs):
        if self.logo_orig and not self.logo_thumb:
            self.logo_thumb = util.create_logo(self.logo_orig.name)
        if not self.name and self.system:
            self.name = self.system.name
        if not self.version_number and self.system:
            if self.system.current_version == 0:
                self.version_number = 0
            else:
                self.version_number = self.system.current_version + 1
            self.system.current_version = self.version_number
            self.system.save()
        super(SystemVersion, self).save(*args, **kwargs)


# CLASS
