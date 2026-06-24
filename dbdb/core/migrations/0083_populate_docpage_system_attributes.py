from django.db import migrations

FIELDS = [
    ('sv-description',    'Description',              "A prose summary of what the system is and the workloads it targets."),
    ('sv-start-year',     'Start Year',               "The year the project was first released or publicly announced."),
    ('sv-end-year',       'End Year',                 "The year active development ceased, if the project is discontinued."),
    ('sv-history',        'History',                  "Narrative of the system’s origins, milestones, and lineage over time."),
    ('sv-developer-orgs', 'Developer Organizations',  "The companies, labs, or communities that build and maintain it."),
    ('sv-country',        'Country of Origin',        "Where the system was first developed."),
    ('sv-system-url',     'System URL',               "The official homepage or product website."),
    ('sv-docs-url',       'Documentation URL',        "Where the official technical documentation is published."),
    ('sv-sourcerepo-url', 'Source Repository URL',    "The public version-control repository, where one exists."),
    ('sv-wikipedia-url',  'Wikipedia URL',            "The system’s Wikipedia article, if available."),
    ('sv-twitter-handle', 'Twitter Handle',           "The project’s account on X / Twitter."),
    ('sv-linkedin-handle','LinkedIn Handle',          "The project or vendor’s LinkedIn page."),
    ('sv-derived-from',   'Derived From',             "Systems whose codebase this one was forked or built from."),
    ('sv-embedded',       'Embedded / Used By',       "Systems that embed or build upon this one as a component."),
    ('sv-inspired-by',    'Inspired By',              "Systems that influenced this one’s design without shared code."),
    ('sv-compatible-with','Compatible With',          "Systems whose wire protocol or dialect this one is compatible with."),
    ('sv-hosted-services','Hosted Services (DBaaS)',  "Managed cloud offerings that run this system as a service."),
]


def create_docpages(apps, schema_editor):
    DocPage = apps.get_model('core', 'DocPage')
    parent = DocPage.objects.create(
        slug='system-attributes',
        title='System Attributes',
        sort_order=0,
    )
    for i, (slug, title, description) in enumerate(FIELDS, start=1):
        DocPage.objects.create(
            slug=slug,
            title=title,
            description=description,
            sort_order=i,
            parent=parent,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0082_docpage_model'),
    ]

    operations = [
        migrations.RunPython(create_docpages, migrations.RunPython.noop),
    ]
