from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dbdb.core.models import Attribute, AttributeOption, Feature, FeatureOption, Organization, System
from dbdb.core.utils.versions import clone_system_version, finalize_new_version


class Command(BaseCommand):
    help = 'Bulk-add an AttributeOption or FeatureOption to matching Systems via new SystemVersions'

    def add_arguments(self, parser):
        attr_grp = parser.add_argument_group('Attribute update (optional)')
        attr_grp.add_argument(
            '--attribute',
            metavar='ATTR',
            help='Attribute slug or name (e.g. "tag" or "Tags")',
        )
        attr_grp.add_argument(
            '--attribute-option',
            dest='attribute_option',
            metavar='OPT',
            help='AttributeOption slug or name within the attribute (e.g. "open-source")',
        )

        feat_grp = parser.add_argument_group('Feature update (optional)')
        feat_grp.add_argument(
            '--feature',
            metavar='FEAT',
            help='Feature slug or label (e.g. "data-model" or "Data Model")',
        )
        feat_grp.add_argument(
            '--feature-option',
            dest='feature_option',
            metavar='OPT',
            help='FeatureOption slug or value within the feature (e.g. "relational")',
        )

        parser.add_argument(
            '--developer',
            metavar='ORG',
            help='Organization slug or name to add as a developer (e.g. "oracle" or "Oracle")',
        )
        parser.add_argument(
            '--creator',
            metavar='USERNAME',
            help='Username of the user to record as version creator (default: first superuser)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without writing to the database.',
        )
        parser.add_argument(
            'keywords',
            nargs='+',
            metavar='KEYWORD',
            help='One or more System name keywords to search (name__icontains)',
        )

    # ── Lookup helpers ─────────────────────────────────────────────────────────

    def _resolve_attribute_option(self, options):
        """Return (Attribute, AttributeOption, sv_field) or raise CommandError."""
        attr_query = options['attribute']
        try:
            attribute = Attribute.objects.get(slug=attr_query)
        except Attribute.DoesNotExist:
            try:
                attribute = Attribute.objects.get(name__iexact=attr_query)
            except Attribute.DoesNotExist:
                raise CommandError(f'Attribute not found: {attr_query!r}')

        if not attribute.sv_field:
            raise CommandError(
                f'Attribute {attribute.name!r} has no sv_field set — '
                'cannot determine which SystemVersion M2M field to update.'
            )

        opt_query = options['attribute_option']
        try:
            attr_option = AttributeOption.objects.select_related('attribute').get(
                attribute=attribute, slug=opt_query,
            )
        except AttributeOption.DoesNotExist:
            try:
                attr_option = AttributeOption.objects.select_related('attribute').get(
                    attribute=attribute, name__iexact=opt_query,
                )
            except AttributeOption.DoesNotExist:
                raise CommandError(
                    f'AttributeOption not found: {opt_query!r} '
                    f'under attribute {attribute.name!r}'
                )

        return attribute, attr_option

    def _resolve_organization(self, name_or_slug):
        """Return Organization or raise CommandError."""
        try:
            return Organization.objects.get(slug=name_or_slug)
        except Organization.DoesNotExist:
            try:
                return Organization.objects.get(name__iexact=name_or_slug)
            except Organization.DoesNotExist:
                raise CommandError(f'Organization not found: {name_or_slug!r}')

    def _resolve_feature_option(self, options):
        """Return (Feature, FeatureOption) or raise CommandError."""
        feat_query = options['feature']
        try:
            feature = Feature.objects.get(slug=feat_query)
        except Feature.DoesNotExist:
            try:
                feature = Feature.objects.get(label__iexact=feat_query)
            except Feature.DoesNotExist:
                raise CommandError(f'Feature not found: {feat_query!r}')

        opt_query = options['feature_option']
        try:
            feat_option = FeatureOption.objects.select_related('feature').get(
                feature=feature, slug=opt_query,
            )
        except FeatureOption.DoesNotExist:
            try:
                feat_option = FeatureOption.objects.select_related('feature').get(
                    feature=feature, value__iexact=opt_query,
                )
            except FeatureOption.DoesNotExist:
                raise CommandError(
                    f'FeatureOption not found: {opt_query!r} '
                    f'under feature {feature.label!r}'
                )

        return feature, feat_option

    # ── Main handler ───────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        has_attr = bool(options.get('attribute') or options.get('attribute_option'))
        has_feat = bool(options.get('feature') or options.get('feature_option'))
        has_dev  = bool(options.get('developer'))

        if not has_attr and not has_feat and not has_dev:
            raise CommandError(
                'Specify at least one of --attribute/--attribute-option, '
                '--feature/--feature-option, or --developer.'
            )

        # ── Resolve Attribute+Option ───────────────────────────────────────────
        attr_option = None
        attribute   = None
        if has_attr:
            if not options.get('attribute') or not options.get('attribute_option'):
                raise CommandError('--attribute and --attribute-option must be used together.')
            attribute, attr_option = self._resolve_attribute_option(options)

        # ── Resolve Feature+Option ─────────────────────────────────────────────
        feat_option = None
        feature     = None
        if has_feat:
            if not options.get('feature') or not options.get('feature_option'):
                raise CommandError('--feature and --feature-option must be used together.')
            feature, feat_option = self._resolve_feature_option(options)

        # ── Resolve developer Organization ─────────────────────────────────────
        dev_org = None
        if has_dev:
            dev_org = self._resolve_organization(options['developer'])

        # ── Resolve creator username ───────────────────────────────────────────
        username = options.get('creator') or None

        # Build the comment string from whatever was supplied
        comment_parts = []
        if attr_option:
            comment_parts.append(f'{attribute.name}→{attr_option.name}')
        if feat_option:
            comment_parts.append(f'{feature.label}→{feat_option.value}')
        if dev_org:
            comment_parts.append(f'developer:{dev_org.name}')
        comment = ', '.join(comment_parts)

        # ── Collect matching Systems (deduplicated across keywords) ────────────
        system_map = {}  # pk → System
        for kw in options['keywords']:
            for system in System.objects.filter(name__icontains=kw).order_by('name'):
                system_map[system.pk] = system
        systems = sorted(system_map.values(), key=lambda s: s.name)

        if not systems:
            self.stdout.write(self.style.WARNING('No systems matched the given keywords.'))
            return

        # ── Process each system ────────────────────────────────────────────────
        rows = []  # (system_name, status, detail)

        with transaction.atomic():
            for system in systems:
                try:
                    current = system.current()
                except Exception as exc:
                    rows.append((system.name, 'ERROR', str(exc), None))
                    continue

                ver_user = username if username else current.creator.username

                # Check if all requested additions are already present → skip
                attr_present = (
                    attr_option is None
                    or getattr(current, attribute.sv_field).filter(pk=attr_option.pk).exists()
                )
                feat_present = (
                    feat_option is None
                    or current.features.filter(
                        feature=feature, options=feat_option
                    ).exists()
                )
                dev_present = (
                    dev_org is None
                    or current.developer_orgs.filter(pk=dev_org.pk).exists()
                )
                if attr_present and feat_present and dev_present:
                    rows.append((system.name, 'SKIPPED', 'option(s) already present', None))
                    continue

                if dry_run:
                    parts = []
                    if not attr_present:
                        parts.append(f'attr:{attr_option.name!r}')
                    if not feat_present:
                        parts.append(f'feat:{feat_option.value!r}')
                    if not dev_present:
                        parts.append(f'developer:{dev_org.name!r}')
                    rows.append((system.name, 'DRY RUN', 'would add ' + ', '.join(parts), ver_user))
                    continue

                new_ver = clone_system_version(
                    current,
                    username=ver_user,
                    comment=comment,
                    attribute_options=[attr_option] if attr_option and not attr_present else None,
                    feature_options=[feat_option] if feat_option and not feat_present else None,
                )
                if dev_org and not dev_present:
                    new_ver.developer_orgs.add(dev_org)
                finalize_new_version(new_ver)
                rows.append((system.name, 'UPDATED', f'v{new_ver.ver}', ver_user))

            if dry_run:
                transaction.set_rollback(True)

        # ── Print results table ────────────────────────────────────────────────
        self.stdout.write('')
        col_name   = max(len('System'), max(len(r[0]) for r in rows))
        col_status = max(len('Status'), max(len(r[1]) for r in rows))
        col_detail = max(len('Detail'), max(len(r[2]) for r in rows))
        col_user = max(len('User'), max(len(r[3]) for r in rows))

        sep = f'+{"-" * (col_name + 2)}+{"-" * (col_status + 2)}+{"-" * (col_detail + 2)}+{"-" * (col_user + 2)}+'
        hdr = f'| {"System":<{col_name}} | {"Status":<{col_status}} | {"Detail":<{col_detail}} | {"User":<{col_user}} |'

        self.stdout.write(sep)
        self.stdout.write(hdr)
        self.stdout.write(sep)
        for name, status, detail, user in rows:
            style = self.style.SUCCESS if status == 'UPDATED' else (
                self.style.WARNING if status in ('SKIPPED', 'DRY RUN') else self.style.ERROR
            )
            self.stdout.write(
                style(f'| {name:<{col_name}} | {status:<{col_status}} | {detail:<{col_detail}} | {user:<{col_user}} |')
            )
        self.stdout.write(sep)

        updated = sum(1 for r in rows if r[1] == 'UPDATED')
        skipped = sum(1 for r in rows if r[1] == 'SKIPPED')
        errors  = sum(1 for r in rows if r[1] == 'ERROR')

        summary = f'\n{len(rows)} system(s) examined'
        if dry_run:
            summary += ' [DRY RUN — no changes written]'
        else:
            summary += f': {updated} updated, {skipped} skipped, {errors} error(s)'
        self.stdout.write(summary)
