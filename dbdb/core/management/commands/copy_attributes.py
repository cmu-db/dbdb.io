"""
Data migration: copies Tag, License, OperatingSystem, ProgrammingLanguage, and ProjectType
rows into Attribute/AttributeOption, then re-links existing SystemVersion M2M relationships
to the new attr_* fields.

Run order:
    1. manage.py migrate          (applies migration 0059 — adds Attribute/AttributeOption tables)
    2. manage.py copy_attributes [--dry-run]
    3. manage.py migrate          (applies migration 0060 — removes old fields, renames attr_* fields)
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from dbdb.core.models import (
    Attribute, AttributeOption,
    License, OperatingSystem, ProgrammingLanguage, ProjectType, SystemVersion, Tag,
)

# Each entry maps a source model → Attribute slug + which old/new SV M2M field names to copy.
# For ProgrammingLanguage the one Attribute backs two separate SV fields.
CONFIGS = [
    {
        'attribute_slug': 'tag',
        'attribute_name': 'Tag',
        'source_model': Tag,
        'pairs': [('tags', 'attr_tags')],
    },
    {
        'attribute_slug': 'project-type',
        'attribute_name': 'Project Type',
        'source_model': ProjectType,
        'pairs': [('project_types', 'attr_project_types')],
    },
    {
        'attribute_slug': 'license',
        'attribute_name': 'License',
        'source_model': License,
        'pairs': [('licenses', 'attr_licenses')],
    },
    {
        'attribute_slug': 'os',
        'attribute_name': 'Operating System',
        'source_model': OperatingSystem,
        'pairs': [('oses', 'attr_oses')],
    },
    {
        'attribute_slug': 'programming-language',
        'attribute_name': 'Programming Language',
        'source_model': ProgrammingLanguage,
        'pairs': [
            ('supported_languages', 'attr_supported_languages'),
            ('written_in', 'attr_written_in'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Migrate Tag/License/OS/ProgrammingLanguage/ProjectType into Attribute/AttributeOption'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be written.\n'))

        total_options = 0
        total_links = 0

        with transaction.atomic():
            for cfg in CONFIGS:
                attr_slug = cfg['attribute_slug']
                attr_name = cfg['attribute_name']
                source_model = cfg['source_model']

                attr, attr_created = Attribute.objects.get_or_create(
                    slug=attr_slug,
                    defaults={'name': attr_name},
                )
                action = 'Created' if attr_created else 'Found existing'
                self.stdout.write(f'{action} Attribute: {attr_name} ({attr_slug})')

                # Build slug→AttributeOption mapping from source rows
                old_id_to_opt = {}
                for old_obj in source_model.objects.all():
                    defaults = {
                        'name': old_obj.name,
                        'url': getattr(old_obj, 'url', '') or '',
                        'icon': getattr(old_obj, 'icon', '') or '',
                        'description': getattr(old_obj, 'description', '') or '',
                    }
                    opt, opt_created = AttributeOption.objects.get_or_create(
                        attribute=attr,
                        slug=old_obj.slug,
                        defaults=defaults,
                    )
                    old_id_to_opt[old_obj.pk] = opt
                    mark = '+' if opt_created else '='
                    self.stdout.write(f'  [{mark}] AttributeOption: {opt.name} ({opt.slug})')
                    if opt_created:
                        total_options += 1

                # Copy M2M links from old SV fields to new attr_* fields
                for old_field, new_field in cfg['pairs']:
                    link_count = 0
                    for sv in SystemVersion.objects.prefetch_related(old_field):
                        old_rels = list(getattr(sv, old_field).all())
                        if not old_rels:
                            continue
                        new_m2m = getattr(sv, new_field)
                        for old_rel in old_rels:
                            opt = old_id_to_opt.get(old_rel.pk)
                            if opt is None:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  WARNING: no AttributeOption for {source_model.__name__} '
                                        f'pk={old_rel.pk} — skipping'
                                    )
                                )
                                continue
                            new_m2m.add(opt)
                            link_count += 1
                    self.stdout.write(
                        f'  Copied {link_count} links: SystemVersion.{old_field} → .{new_field}'
                    )
                    total_links += link_count

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {total_options} new AttributeOption rows, {total_links} M2M links copied.'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('(dry run — all changes rolled back)'))