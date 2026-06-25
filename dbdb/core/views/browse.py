import collections
import re
import urllib.parse
from dataclasses import asdict
from functools import reduce
from operator import and_, or_

from django.contrib.postgres.aggregates import JSONBAgg
from django.contrib.postgres.search import SearchQuery
from django.db.models import Count, F, Max, Min, Q
from django.db.models.expressions import RawSQL
from django.db.models.functions import JSONObject
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.html import mark_safe
from django.views import View
from django.views.decorators.cache import cache_control

from django_countries import countries
from django_countries.fields import Country as CountryObj

from dbdb.core.common.searchvector import SearchVector
from dbdb.core.templatetags.savedsearch_tags import ss_decode
from dbdb.core.models import (
    Attribute,
    AttributeOption,
    Feature,
    FeatureOption,
    Organization,
    SavedSearch,
    System,
    SystemFeature,
    SystemSearchText,
    SystemVersion,
)
from dbdb.core.utils.filters import FilterChoice, FilterGroup


ColumnDef = collections.namedtuple('ColumnDef', ['col_id', 'label', 'col_type'])

DEFAULT_COLS = ['data-model', 'start-year', 'tags']

_BUILTIN_COLUMNS = [
    ColumnDef('tags',             'Tags',              'builtin'),
    ColumnDef('start-year',       'Start Year',        'builtin'),
    ColumnDef('end-year',         'End Year',          'builtin'),
    ColumnDef('developer-orgs',   'Developer',         'builtin'),
    ColumnDef('acquired-by',      'Acquired By',       'builtin'),
    ColumnDef('country',          'Country of Origin', 'builtin'),
    ColumnDef('system-url',       'Website URL',       'builtin'),
    ColumnDef('docs-url',         'Documentation',     'builtin'),
    ColumnDef('sourcerepo-url',   'Source Repo',       'builtin'),
    ColumnDef('wikipedia-url',    'Wikipedia',         'builtin'),
    ColumnDef('twitter-handle',   'Twitter',           'builtin'),
    ColumnDef('former-names',     'Former Names',      'builtin'),
]

# Maps URL col_id → FK traversal path on SystemVersion
_URL_COL_FIELDS = {
    'system-url':     'system_url__url',
    'docs-url':       'docs_url__url',
    'sourcerepo-url': 'sourcerepo_url__url',
    'wikipedia-url':  'wikipedia_url__url',
}

_RELATIONSHIP_COLUMNS = [
    ColumnDef('compatible-with', 'Compatible With', 'relationship'),
    ColumnDef('derived-from',    'Derived From',    'relationship'),
    ColumnDef('embedded',        'Embeds / Uses',   'relationship'),
    ColumnDef('hosted-services', 'Hosted Services', 'relationship'),
    ColumnDef('inspired-by',     'Inspired By',     'relationship'),
]

# Maps relationship col_id → (SystemVersion M2M field name, null-check field)
_RELATIONSHIP_FIELD_MAP = {
    'compatible-with': 'compatible_with',
    'derived-from':    'derived_from',
    'embedded':        'embedded',
    'hosted-services': 'hosted_services',
    'inspired-by':     'inspired_by',
}

_YEAR_IDS        = frozenset({'start-year', 'end-year'})
_FIXED_RIGHT_IDS = frozenset({'tags'})

# Maps a search GET param to the column ID that should be auto-shown when that param is active.
_SEARCH_PARAM_TO_COL = {
    'developer':   'developer-orgs',
    'acquired-by': 'acquired-by',
    'country':     'country',
    'compatible':  'compatible-with',
    'derived':     'derived-from',
    'embeds':      'embedded',
    'hosted_by':   'hosted-services',
    'inspired':    'inspired-by',
}

# Maps GET param → (verb_phrase, noun_label) for title generation.
# verb_phrase: prepended to resolved names in normal filter titles (None if only used for existence).
# noun_label: used in existence-query titles ("with {noun_label}").
_FIELD_NAME_MAP = {
    'compatible':     ('Compatible With', 'Compatibility'),
    'derived':        ('Derived From',    'Derivation'),
    'embeds':         ('Using',           'Embedded Systems'),
    'hosted_by':      ('Hosting',         'Hosted Service'),
    'inspired':       ('Inspired By',     'Inspiration'),
    'developer':      ('Developed By',    'Developer Organization'),
    'acquired-by':    ('Acquired By',     'Acquisition'),
    'country':        ('from',            'Country'),
    'wikipedia_url':  (None, 'Wikipedia URL'),
    'system_url':     (None, 'Website URL'),
    'docs_url':       (None, 'Docs URL'),
    'sourcerepo_url': (None, 'Source Code URL'),
    'description':    (None, 'Description'),
    'history':        (None, 'History'),
}

# Maps GET param → (orm_lookup, orm_value) for existence queries (param value == '*').
# Features and attributes are handled dynamically and are not in this map.
_EXISTS_FILTER_MAP = {
    'wikipedia_url':  ('wikipedia_url__isnull',  False),
    'system_url':     ('system_url__isnull',      False),
    'docs_url':       ('docs_url__isnull',         False),
    'sourcerepo_url': ('sourcerepo_url__isnull',   False),
    'description':    ('description__gt',          ''),
    'history':        ('history__gt',              ''),
    'developer':      ('developer_orgs__isnull',   False),
    'acquired-by':    ('acquisitions__isnull',      False),
    'compatible':     ('compatible_with__isnull',   False),
    'derived':        ('derived_from__isnull',      False),
    'embeds':         ('embedded__isnull',          False),
    'hosted_by':      ('hosted_services__isnull',   False),
    'inspired':       ('inspired_by__isnull',       False),
}

_DOI_RE = re.compile(r'\b10\.\d{4,}/\S+', re.IGNORECASE)

def _is_doi_query(q: str) -> bool:
    return 'doi.org' in q.lower() or bool(_DOI_RE.search(q))

def _doi_warning_html(q: str):
    return mark_safe(
        'This site is for searching database management systems, not academic publications. '
        'If you are looking for a paper, please use '
        '<a href="https://scholar.google.com/" target="_blank" rel="noopener">Google Scholar</a> or '
        '<a href="https://www.semanticscholar.org/" target="_blank" rel="noopener">Semantic Scholar</a>.'
    )

_PRESERVE_CASE_PARAMS = frozenset({'q', 'ss'})

def _normalize_get(qd):
    """Return a mutable QueryDict with all keys and values lowercased.
    Preserves original case for 'q' (search text) and 'ss' (signed token)."""
    from django.http import QueryDict
    result = QueryDict(mutable=True)
    for key in qd.keys():
        norm_key = key.lower()
        for val in qd.getlist(key):
            result.appendlist(norm_key, val if norm_key in _PRESERVE_CASE_PARAMS else val.lower())
    return result

# Maps logical order-by names (from the ?order-by= param) to annotated/ORM field names.
# 'name' and 'slug' are available because they are annotated onto the queryset before .values().
_ORDER_BY_MAP = {
    'name':       'name',
    'start-year': 'start_year',
    'end-year':   'end_year',
    'created':    'created',
}


# ==============================================
# BrowseView
# ==============================================
@method_decorator(cache_control(public=True, max_age=14400), name='dispatch')
class BrowseView(View):

    template_name = 'core/browse.html'

    def build_filter_group_for_field(self, field, search_field, label, all_systems, querydict):
        empty_set = set()
        values = SystemVersion.objects.filter(is_current=True)\
                        .filter(~Q(**{field: None}))\
                        .values_list(field)
                        # .distinct() \
                        # .order_by()
        fg = FilterGroup(search_field, label, sorted([
            FilterChoice(
                all_systems[v[0]].slug,
                all_systems[v[0]].name,
                # False
            )
            for v in set(values)
            #for sys in System.objects.values_list('id','slug','name', named=True)
        ], key=lambda x: x.label))
        return fg

    def build_filter_groups(self, querydict):
        empty_set = set()

        # def prepare(fg):
        #     for i,choice in enumerate(fg.choices):
        #         if i >= FILTERGROUP_VISIBLE_LENGTH:
        #             choice.is_hidden = True
        #             fg.has_more = True
        #     return fg

        def reduce_feature_options(mapping, option):
            mapping[option.feature_id].choices.append(
                FilterChoice(
                    option.slug,
                    option.value,
                    # False
                )
            )
            return mapping

        other_filtersgroups = []

        # Countries
        def reduce_countries(mapping, item):
            countries = item.countries.split(',')
            for c in countries:
                if c: mapping[c] = mapping.get(c, 0) + 1
            return mapping

        system_countries = SystemVersion.objects \
            .filter(is_current=True) \
            .values_list('countries', named=True)
        system_countries = reduce(reduce_countries, system_countries, {})

        countries_map = dict(countries)

        fg_country = FilterGroup('country', 'Country', sorted([
            FilterChoice(
               code,
               countries_map[code], # name
            #    False
            )
            for code in map(str.upper, system_countries.keys())
        ], key=lambda x: x.label))
        other_filtersgroups.append(fg_country)

        all_systems = dict([
            (sys.id, sys)
            for sys in System.objects.values_list('id','slug','name', named=True)
        ])

        # Compatible
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'compatible_with', \
            'compatible', \
            'Compatible With', \
            all_systems, \
            querydict
        ))

        # Embedded
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'embedded', \
            'embeds', \
            'Embeds / Uses', \
            all_systems, \
            querydict
        ))

        # Derived
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'derived_from', \
            'derived', \
            'Derived From', \
            all_systems, \
            querydict
        ))

        # Inspired
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'inspired_by', \
            'inspired', \
            'Inspired By', \
            all_systems, \
            querydict
        ))

        # Hosted By
        other_filtersgroups.append(self.build_filter_group_for_field(\
            'hosted_services', \
            'hosted_by', \
            'Hosted By', \
            all_systems, \
            querydict
        ))

        # Developer Orgs
        developer_org_slugs = set(
            SystemVersion.objects
            .filter(is_current=True, developer_orgs__isnull=False)
            .values_list('developer_orgs__slug', flat=True)
            .distinct()
        )
        developer_orgs_map = {
            o.slug: o.name
            for o in Organization.objects.filter(slug__in=developer_org_slugs).only('slug', 'name')
        }
        other_filtersgroups.append(FilterGroup('developer', 'Developer', sorted([
            FilterChoice(slug, name)
            for slug, name in developer_orgs_map.items()
        ], key=lambda x: x.label)))

        # Acquired By
        acquiredby_org_slugs = set(
            SystemVersion.objects
            .filter(is_current=True, acquisitions__isnull=False)
            .values_list('acquisitions__organization__slug', flat=True)
            .distinct()
        )
        acquiredby_orgs_map = {
            o.slug: o.name
            for o in Organization.objects.filter(slug__in=acquiredby_org_slugs).only('slug', 'name')
        }
        other_filtersgroups.append(FilterGroup('acquired-by', 'Acquired By', sorted([
            FilterChoice(slug, name)
            for slug, name in acquiredby_orgs_map.items()
        ], key=lambda x: x.label)))

        # Add one FilterGroup per Attribute that has a sv_field configured.
        # Adding a new Attribute in the admin automatically shows up here.
        for attr in Attribute.objects.filter(sv_field__gt='').prefetch_related('options').order_by('name'):
            other_filtersgroups.append(FilterGroup(
                attr.slug,
                attr.name,
                [FilterChoice(opt.slug, opt.name) for opt in attr.options.order_by('name')],
            ))

        # build from list of features (alphabetical order)
        filtergroups = collections.OrderedDict(
            (
                f_id,
                FilterGroup(f_slug, f_label, []),
            )
            for f_id,f_slug,f_label in Feature.objects.all().order_by('label').values_list('id','slug','label')
        )

        # add feature options to features
        filtergroups = reduce(
            reduce_feature_options,
            FeatureOption.objects.all().order_by('value').values_list('feature_id','feature__slug','id','slug','value', named=True),
            filtergroups
        )

        filtergroups = other_filtersgroups + list( filtergroups.values() )

        return filtergroups

    def slug_to_system(self, slugs):
        slugs = { s.strip() for s in slugs }
        systems = System.objects.filter(slug__in=slugs)
        return { s.slug : s for s in systems }
    ## DEF


    def do_search(self, get_params, sqs, search_op):
        has_search = False

        countries_map = dict(countries)

        # map feature slugs to ids
        features_map = {
            f_slug : f_id
            for f_id,f_slug in Feature.objects.all().order_by().values_list('id','slug')
        }

        # map feature options slugs to ids, and slugs to display names
        _fo_rows = FeatureOption.objects.all().order_by().values_list('feature_id','id','slug','value')
        featuresoptions_map = {(f_id, fo_slug): fo_id for f_id, fo_id, fo_slug, _ in _fo_rows}
        featureoptions_name_map = {(f_id, fo_slug): fo_value for f_id, _, fo_slug, fo_value in _fo_rows}

        # pull search criteria
        search_q = get_params.get('q', '').strip()

        def _is_count_val(v):
            return v.startswith('+') and v[1:].isdigit()

        # separate option-slug values from count (+N) values for feature params
        search_fg = {}
        feature_counts = {}
        feature_exists = {}  # fid → slug, for existence queries (value == '*')
        for k in get_params.keys():
            if k not in features_map:
                continue
            fid = features_map[k]
            vals = get_params.getlist(k)
            if vals == ['*']:
                feature_exists[fid] = k
                continue
            option_vals = [v for v in vals if not _is_count_val(v)]
            count_vals  = [v for v in vals if _is_count_val(v)]
            if option_vals:
                search_fg[fid] = set(option_vals)
            if count_vals:
                feature_counts[fid] = max(int(v[1:]) for v in count_vals)

        # define date filters
        search_start_year = get_params.get('start-year', '').strip()
        search_start_min = get_params.get('start-min', '').strip()
        search_start_max = get_params.get('start-max', '').strip()
        search_end_year = get_params.get('end-year', '').strip()
        search_end_min = get_params.get('end-min', '').strip()
        search_end_max = get_params.get('end-max', '').strip()

        # define static filters
        search_acquiredby = get_params.getlist('acquired-by')
        search_compatible = get_params.getlist('compatible')
        search_country = list(map(str.upper, get_params.getlist('country')))
        search_derived = get_params.getlist('derived')
        search_developer = get_params.getlist('developer')
        search_embeds = get_params.getlist('embeds')
        search_hosted_by = get_params.getlist('hosted_by')
        search_inspired = get_params.getlist('inspired')
        search_suffix = get_params.getlist('suffix')

        # collect attribute-based search params keyed by Attribute slug
        attr_searches = {}
        attr_count_searches = {}
        attr_exists = {}  # attr.slug → attr, for existence queries (value == '*')
        for attr in Attribute.objects.filter(sv_field__gt='').only('slug', 'name', 'sv_field', 'search_text'):
            vals = get_params.getlist(attr.slug)
            if not vals:
                continue
            if vals == ['*']:
                attr_exists[attr.slug] = attr
                continue
            option_vals = [v for v in vals if not _is_count_val(v)]
            count_vals  = [v for v in vals if _is_count_val(v)]
            if option_vals:
                attr_searches[attr.slug] = (attr, option_vals)
            if count_vals:
                attr_count_searches[attr.slug] = (attr, max(int(v[1:]) for v in count_vals))

        # collect filters
        search_mapping = {
            'query': search_q,

            'start_year': search_start_year,
            'start_min': search_start_min,
            'start_max': search_start_max,
            'end_year': search_end_year,
            'end_min': search_end_min,
            'end_max': search_end_max,

            'acquired-by': search_acquiredby,
            'compatible': search_compatible,
            'country': search_country,
            'derived': search_derived,
            'developer': search_developer,
            'embeds': search_embeds,
            'hosted_by': search_hosted_by,
            'inspired': search_inspired,
            'suffix': search_suffix,
        }
        # Include attribute and count params so the early-return check counts them
        for slug, (attr, vals) in attr_searches.items():
            search_mapping[slug] = vals
        for slug, (attr, min_count) in attr_count_searches.items():
            search_mapping[f'{slug}__gte'] = min_count
        for fid, min_count in feature_counts.items():
            search_mapping[f'feature_{fid}__gte'] = min_count
        for param in _EXISTS_FILTER_MAP:
            if get_params.get(param) == '*':
                search_mapping[param] = '*'
        for slug in attr_exists:
            search_mapping[slug] = '*'
        for fid, slug in feature_exists.items():
            search_mapping[slug] = '*'

        if not any(search_mapping.values()) and not any(search_fg):
            return (sqs, { }, 'Browse', None)

        title = 'Databases '
        op_str = 'and' if search_op == and_ else 'or'

        # search_badges = []

        # apply keyword search to name (require all terms)
        if search_q:
            search_vector = SearchVector('search_text', config='simple')
            # Use prefix matching (term:*) so partial inputs like "Citrus" match
            # lexemes like "Citrusleaf" in search_text. The existing GIN index
            # supports :* natively, so no index change is needed.
            raw_tsquery = ' & '.join(f'{term}:*' for term in search_q.split())
            search_query = SearchQuery(raw_tsquery, config='simple', search_type='raw')

            # name__icontains keeps mid-word partial matches on the system name
            # (e.g. "iger" → WiredTiger) that prefix FTS would miss.
            matches = SystemSearchText.objects \
                .annotate(search=search_vector) \
                .filter(Q(name__icontains=search_q) | Q(search=search_query)) \
                .values('system_id')
            sqs = sqs.filter(system_id__in=[x['system_id'] for x in matches])

        sqs_filters = []

        # apply year limits
        if search_start_year.isdigit():
            sqs = sqs.filter(start_year=int(search_start_year))
            title += f' Started in {search_start_year}'
            pass
        if search_start_min.isdigit():
            sqs = sqs.filter(start_year__gte=int(search_start_min))
            title += f' Started in {search_start_min}'
            pass
        if search_start_max.isdigit():
            sqs = sqs.filter(start_year__lte=int(search_start_max))

            if search_start_min.isdigit():
                title += f'-{search_start_max}'
            else:
                title += f' Started Before {search_start_max}'
            pass
        if search_end_year.isdigit():
            sqs = sqs.filter(end_year=int(search_end_year))
            title += f' Ended in {search_end_year}'
            pass
        if search_end_min.isdigit():
            sqs = sqs.filter(end_year__gte=int(search_end_min))
            if search_start_min or search_start_max:
                title += f' and Ended in {search_end_min}'
            else:
                title += f' Ended in {search_end_min}'
            pass
        if search_end_max.isdigit():
            sqs = sqs.filter(end_year__lte=int(search_end_max))
            if search_end_min.isdigit():
                title += f'-{search_end_max}'
            else:
                title += f' Ended Before {search_end_max}'
            pass

        search_parts = []
        # search - country
        if search_country:
            sqs_filters.append(Q(countries__in=search_country))
            country_names = [(countries_map.get(c) if countries_map.get(c) else '') for c in search_country]
            search_countries = ' or '.join(country_names) if len(country_names) < 3 else f"{', '.join(country_names[:-1])}, or {country_names[-1]}"
            if search_countries:
                _v, _ = _FIELD_NAME_MAP['country']
                search_parts.append(f' {_v} ' + search_countries)
            pass

        # search - compatible
        if search_compatible:
            sqs_filters.append(Q(compatible_with__slug__in=search_compatible))

            systems = self.slug_to_system(search_compatible)
            search_mapping['compatible'] = systems.values()

            system_names = [str(e) for e in search_mapping['compatible']]
            search_compatiblewith = ' or '.join(system_names) if len(system_names) < 3 else f"{', '.join(system_names[:-1])}, or {system_names[-1]}"
            if search_compatiblewith:
                _v, _ = _FIELD_NAME_MAP['compatible']
                search_parts.append(f' {_v} ' + search_compatiblewith)
            pass

        # search - derived from
        if search_derived:
            sqs_filters.append(Q(derived_from__slug__in=search_derived))
            systems = self.slug_to_system(search_derived)
            search_mapping['derived'] = systems.values()

            system_names = [str(e) for e in search_mapping['derived']]
            search_compatiblewith = ' or '.join(system_names) if len(system_names) < 3 else f"{', '.join(system_names[:-1])}, or {system_names[-1]}"
            if search_compatiblewith:
                _v, _ = _FIELD_NAME_MAP['derived']
                search_parts.append(f' {_v} ' + search_compatiblewith)
            pass

        # search - embedded
        if search_embeds:
            sqs_filters.append(Q(embedded__slug__in=search_embeds))
            systems = self.slug_to_system(search_embeds)
            search_mapping['embeds'] = systems.values()

            system_names = [str(e) for e in search_mapping['embeds']]
            search_compatiblewith = ' or '.join(system_names) if len(system_names) < 3 else f"{', '.join(system_names[:-1])}, or {system_names[-1]}"
            if search_compatiblewith:
                _v, _ = _FIELD_NAME_MAP['embeds']
                search_parts.append(f' {_v} ' + search_compatiblewith)
            pass

        # search - hosted by
        if search_hosted_by:
            sqs_filters.append(Q(hosted_services__slug__in=search_hosted_by))
            systems = self.slug_to_system(search_hosted_by)
            search_mapping['hosted_by'] = systems.values()

            system_names = [str(e) for e in search_mapping['hosted_by']]
            search_hostedby = ' or '.join(system_names) if len(system_names) < 3 else f"{', '.join(system_names[:-1])}, or {system_names[-1]}"
            if search_hostedby:
                _v, _ = _FIELD_NAME_MAP['hosted_by']
                search_parts.append(f' {_v} ' + search_hostedby)
            pass

        # search - inspired by
        if search_inspired:
            sqs_filters.append(Q(inspired_by__slug__in=search_inspired))
            systems = self.slug_to_system(search_inspired)
            search_mapping['inspired'] = systems.values()

            system_names = [str(e) for e in search_mapping['inspired']]
            search_compatiblewith = ' or '.join(system_names) if len(system_names) < 3 else f"{', '.join(system_names[:-1])}, or {system_names[-1]}"
            if search_compatiblewith:
                _v, _ = _FIELD_NAME_MAP['inspired']
                search_parts.append(f' {_v} ' + search_compatiblewith)
            pass

        # search - developer orgs
        if search_developer:
            sqs_filters.append(Q(developer_orgs__slug__in=search_developer))
            orgs = Organization.objects.filter(slug__in=search_developer).only('name')
            org_names = [o.name for o in orgs]
            joined = ' or '.join(org_names) if len(org_names) < 3 else f"{', '.join(org_names[:-1])}, or {org_names[-1]}"
            if joined:
                _v, _ = _FIELD_NAME_MAP['developer']
                search_parts.append(f' {_v} {joined}')
            pass

        # search - acquired by
        if search_acquiredby:
            sqs_filters.append(Q(acquisitions__organization__slug__in=search_acquiredby))
            orgs = Organization.objects.filter(slug__in=search_acquiredby).only('name')
            org_names = [o.name for o in orgs]
            joined = ' or '.join(org_names) if len(org_names) < 3 else f"{', '.join(org_names[:-1])}, or {org_names[-1]}"
            if joined:
                _v, _ = _FIELD_NAME_MAP['acquired-by']
                search_parts.append(f' {_v} {joined}')
            pass

        # search - attribute options (dynamic: one block per Attribute)
        for slug, (attr, param_slugs) in attr_searches.items():
            if search_op == and_ and len(param_slugs) > 1:
                # AND: must have ALL selected options — intersect one queryset per slug
                version_ids = None
                for param_slug in param_slugs:
                    qs = (
                        SystemVersion.objects
                        .filter(is_current=True)
                        .filter(**{f'{attr.sv_field}__slug': param_slug})
                        .values_list('id', flat=True)
                        .distinct()
                    )
                    version_ids = qs if version_ids is None else version_ids.intersection(qs)
                sqs_filters.append(Q(id__in=version_ids))
            else:
                sqs_filters.append(Q(**{f'{attr.sv_field}__slug__in': param_slugs}))
            matched = AttributeOption.objects.filter(attribute=attr, slug__in=param_slugs)
            names = [o.name for o in matched]
            joined = f' {op_str} '.join(names) if len(names) < 3 else f"{', '.join(names[:-1])}, {op_str} {names[-1]}"
            if joined and attr.search_text:
                search_parts.append(attr.search_text.format(names=joined))

        # search - attribute counts (+N): SystemVersions with >= N options for that attribute
        for slug, (attr, min_count) in attr_count_searches.items():
            version_ids = (
                SystemVersion.objects
                .filter(is_current=True)
                .annotate(_cnt=Count(attr.sv_field))
                .filter(_cnt__gte=min_count)
                .values_list('id', flat=True)
            )
            sqs_filters.append(Q(id__in=list(version_ids)))
            search_parts.append(f'at least {min_count} {attr.name}')

        # search - feature counts (+N): SystemVersions with >= N options for that feature
        for fid, min_count in feature_counts.items():
            version_ids = (
                SystemFeature.objects
                .filter(feature_id=fid, version__is_current=True)
                .annotate(_cnt=Count('options'))
                .filter(_cnt__gte=min_count)
                .values_list('version_id', flat=True)
            )
            sqs_filters.append(Q(id__in=list(version_ids)))
            reverse_features_map_local = {v: k for k, v in features_map.items()}
            feat_label = reverse_features_map_local.get(fid, str(fid)).replace('-', ' ').title()
            search_parts.append(f'at least {min_count} {feat_label}')

        # search - suffixes
        if search_suffix:
            for suffix in search_suffix:
                sqs_filters.append(Q(system__name__icontains=suffix))
            pass

        # validate feature option slugs — reject unknown values with an error
        reverse_features_map = {v: k for k, v in features_map.items()}
        for feature_id, option_slugs in search_fg.items():
            for slug in option_slugs:
                if (feature_id, slug) not in featuresoptions_map:
                    feature_name = reverse_features_map.get(feature_id, str(feature_id))
                    return (sqs.none(), {}, 'Invalid Search',
                            f"Unknown value '{slug}' for feature '{feature_name}'.")

        # convert feature option slugs to IDs to do search by filtering
        feature_option_ids = set()
        for feature_id,option_slugs in search_fg.items():
            option_ids = {featuresoptions_map[(feature_id, s)] for s in option_slugs}
            feature_option_ids.update(option_ids)
            pass

        # if there are filter options to search for, apply filter
        if feature_option_ids:
            # Build option_id → feature_id map so inherited queries know which feature to follow.
            option_id_to_feature_id = {}
            for fid, option_slugs in search_fg.items():
                for slug in option_slugs:
                    option_id_to_feature_id[featuresoptions_map[(fid, slug)]] = fid

            def _effective_version_ids(option_id):
                """Version IDs that match option_id directly or via SystemFeature.system inheritance."""
                fid = option_id_to_feature_id[option_id]
                direct = set(
                    SystemFeature.objects
                    .filter(options__id=option_id, version__is_current=True)
                    .values_list('version_id', flat=True)
                )
                # Two-step to avoid an unsupported double reverse-FK traversal:
                # Step 1 — which Systems have the option on their current version?
                parent_system_ids = (
                    SystemFeature.objects
                    .filter(feature_id=fid, options__id=option_id, version__is_current=True)
                    .values('version__system_id')
                )
                # Step 2 — child versions whose SystemFeature.system points to those parents
                inherited = set(
                    SystemFeature.objects
                    .filter(
                        feature_id=fid,
                        version__is_current=True,
                        system__isnull=False,
                        system_id__in=parent_system_ids,
                    )
                    .values_list('version_id', flat=True)
                )
                return direct | inherited

            # OR Queries (Match Any)
            if search_op == or_:
                combined: set = set()
                for oid in feature_option_ids:
                    combined |= _effective_version_ids(oid)
                feature_systems_versions = combined

            # AND Queries (Match All)
            else:
                feature_systems_versions = None
                for oid in feature_option_ids:
                    ids = _effective_version_ids(oid)
                    if feature_systems_versions is None:
                        feature_systems_versions = ids
                    else:
                        feature_systems_versions &= ids
                if feature_systems_versions is None:
                    feature_systems_versions = set()

            sqs_filters.append(Q(id__in=feature_systems_versions))

        if sqs_filters:
            query = reduce(search_op, sqs_filters)
            sqs = sqs.filter(query)

        # Apply existence filters (=*) — always AND'd, never part of search_op reduce
        for param, (lookup, val) in _EXISTS_FILTER_MAP.items():
            if get_params.get(param) == '*':
                sqs = sqs.filter(id__in=
                    SystemVersion.objects.filter(is_current=True)
                    .filter(**{lookup: val}).values('id').distinct()
                )
        for fid in feature_exists:
            sqs = sqs.filter(id__in=
                SystemFeature.objects.filter(feature_id=fid, version__is_current=True)
                .values('version_id').distinct()
            )
        for slug, attr in attr_exists.items():
            sqs = sqs.filter(id__in=
                SystemVersion.objects.filter(is_current=True)
                .filter(**{f'{attr.sv_field}__isnull': False})
                .values('id').distinct()
            )

        # Existence title parts
        for param, (lookup, val) in _EXISTS_FILTER_MAP.items():
            if get_params.get(param) == '*':
                _, noun = _FIELD_NAME_MAP[param]
                search_parts.append(f' with {noun}')
        for fid, slug in feature_exists.items():
            label = slug.replace('-', ' ').title()
            search_parts.append(f' with {label}')
        for slug, attr in attr_exists.items():
            search_parts.append(f' with {attr.name}')

        # Build Title with features
        feature_parts = []
        for key in search_fg:
            names = [
                featureoptions_name_map.get((key, slug), slug)
                for slug in search_fg[key]
            ]
            feature_options = ' or '.join(names) if len(names) < 3 else f"{', '.join(names[:-1])}, or {names[-1]}"
            feature = reverse_features_map[key].replace('-', ' ').title()
            feature_parts.append(f'{feature_options} {feature}')

        query_parts = []
        if search_parts:
            query_parts.append(f' {op_str} '.join(search_parts) if len(search_parts) < 3 else f"{', '.join(search_parts[:-1])}, {op_str} {search_parts[-1]}")
        if feature_parts:
            query_parts.append(' with ' + f' {op_str} '.join(feature_parts))

        title += f' {op_str} '.join(query_parts)

        if title == 'Databases ':
            title = f"Databases matching '{search_q}'" if search_q else 'Browse'
        if len(title) > 60:
            title = title[:60] + '...'

        return (sqs, search_mapping, title, None)

    def get_available_columns(self):
        cols = list(_BUILTIN_COLUMNS) + list(_RELATIONSHIP_COLUMNS)
        for feature in Feature.objects.all().order_by('label'):
            cols.append(ColumnDef(feature.slug, feature.label, 'feature'))
        for attr in Attribute.objects.filter(sv_field__gt='').exclude(slug='tag').order_by('name'):
            cols.append(ColumnDef(attr.slug, attr.name, 'attribute'))
        return cols

    def get_active_columns(self, get_params, available_cols, extra_slugs=()):
        available_map = {c.col_id: c for c in available_cols}
        cols_param = get_params.get('cols', '').strip()
        if cols_param:
            selected_ids = [c.strip() for c in cols_param.split(',') if c.strip() in available_map]
        else:
            selected_ids = list(DEFAULT_COLS)
        is_custom = set(selected_ids) != set(DEFAULT_COLS)

        for slug in extra_slugs:
            if slug in available_map and slug not in selected_ids:
                selected_ids.append(slug)
        cols = [available_map[c] for c in selected_ids if c in available_map]
        # Canonical order: year cols → all content cols → tags
        year_cols    = [c for c in cols if c.col_id in _YEAR_IDS]
        tags_cols    = [c for c in cols if c.col_id in _FIXED_RIGHT_IDS]
        content_cols = [c for c in cols if c.col_id not in _YEAR_IDS and c.col_id not in _FIXED_RIGHT_IDS]
        return (year_cols + content_cols + tags_cols, is_custom)

    def do_dym(self, search_q):
        """Did you mean search"""
        matches = System.objects.annotate(rank=RawSQL("name <-> %s", [search_q])).order_by("rank").values("id", "name", "slug")[:1]
        return matches[0]

    def get(self, request):
        get_params = _normalize_get(request.GET)

        # handle older filter group urls
        if any(filter(lambda k: k.startswith('fg'), get_params.keys())):
           return self.handle_old_urls(request)

        # Search Query
        search_q = get_params.get('q', '').strip()

        # Search Operator (AND vs. OR)
        search_op = get_params.get('search_op', 'or').strip()
        search_op = and_ if search_op == 'and' else or_

        # Determine active columns (before search so we can auto-add searched ones)
        available_columns = self.get_available_columns()
        available_col_ids = {c.col_id for c in available_columns}
        feature_slugs_set = set(Feature.objects.values_list('slug', flat=True))
        attr_slugs_set = set(
            Attribute.objects.filter(sv_field__gt='').exclude(slug='tag').values_list('slug', flat=True)
        )
        searched_slugs = [k for k in get_params.keys() if k in feature_slugs_set or k in attr_slugs_set]
        for param, col_id in _SEARCH_PARAM_TO_COL.items():
            if get_params.get(param) and col_id not in searched_slugs:
                searched_slugs.append(col_id)

        # Parse order-by early so the sorted column can be auto-included in the display
        order_by_raw = get_params.get('order-by', '').strip()
        order_col_key = order_by_raw.lstrip('+-') if order_by_raw else ''
        if order_col_key and order_col_key in available_col_ids and order_col_key not in searched_slugs:
            searched_slugs.append(order_col_key)

        active_columns, cols_are_custom = self.get_active_columns(get_params, available_columns, searched_slugs)
        active_col_ids = [c.col_id for c in active_columns]

        results = SystemVersion.objects.filter(is_current=True)
        results, search_keys, title, search_error = self.do_search(get_params, results, search_op)

        # Base annotations (always)
        results = results.annotate(
            name=F('system__name'),
            slug=F('system__slug'),
            system_tags=JSONBAgg(JSONObject(name=F('tags__name'), slug=F('tags__slug'), icon=F('tags__icon')), filter=Q(tags__isnull=False), distinct=True)
        )

        # Attribute column annotations (inline)
        attr_by_slug = {a.slug: a for a in Attribute.objects.filter(sv_field__gt='').exclude(slug='tag')}
        attr_cols = [c for c in active_columns if c.col_type == 'attribute']
        for col in attr_cols:
            attr = attr_by_slug[col.col_id]
            sv_f = attr.sv_field
            key = 'col_' + col.col_id.replace('-', '_')
            results = results.annotate(**{key: JSONBAgg(
                JSONObject(name=F(f'{sv_f}__name'), slug=F(f'{sv_f}__slug'), icon=F(f'{sv_f}__icon')),
                filter=Q(**{f'{sv_f}__isnull': False}),
                distinct=True,
            )})

        # Developer orgs column annotation (inline)
        if 'developer-orgs' in active_col_ids:
            results = results.annotate(col_developer_orgs=JSONBAgg(
                JSONObject(name=F('developer_orgs__name'), slug=F('developer_orgs__slug'), org_type=F('developer_orgs__org_type')),
                filter=Q(developer_orgs__isnull=False),
                distinct=True,
            ))

        # Acquired-by column annotation (inline)
        if 'acquired-by' in active_col_ids:
            results = results.annotate(col_acquired_by=JSONBAgg(
                JSONObject(name=F('acquisitions__organization__name'), slug=F('acquisitions__organization__slug'), org_type=F('acquisitions__organization__org_type')),
                filter=Q(acquisitions__isnull=False),
                distinct=True,
            ))

        # Relationship column annotations (derived_from, embedded, etc.)
        for col_id, sv_field in _RELATIONSHIP_FIELD_MAP.items():
            if col_id in active_col_ids:
                key = 'col_' + col_id.replace('-', '_')
                results = results.annotate(**{key: JSONBAgg(
                    JSONObject(name=F(f'{sv_field}__name'), slug=F(f'{sv_field}__slug')),
                    filter=Q(**{f'{sv_field}__isnull': False}),
                    distinct=True,
                )})

        # URL column annotations (system_url, docs_url, sourcerepo_url, wikipedia_url)
        for col_id, fk_path in _URL_COL_FIELDS.items():
            if col_id in active_col_ids:
                key = 'col_' + col_id.replace('-', '_')
                results = results.annotate(**{key: F(fk_path)})

        value_fields = ['id', 'name', 'slug', 'logo', 'logo_color', 'start_year', 'end_year', 'system_tags', 'created']
        for col in attr_cols:
            value_fields.append('col_' + col.col_id.replace('-', '_'))
        if 'developer-orgs' in active_col_ids:
            value_fields.append('col_developer_orgs')
        if 'acquired-by' in active_col_ids:
            value_fields.append('col_acquired_by')
        if 'country' in active_col_ids:
            value_fields.append('countries')
        for col_id in _RELATIONSHIP_FIELD_MAP:
            if col_id in active_col_ids:
                value_fields.append('col_' + col_id.replace('-', '_'))
        for col_id in _URL_COL_FIELDS:
            if col_id in active_col_ids:
                value_fields.append('col_' + col_id.replace('-', '_'))
        if 'twitter-handle' in active_col_ids:
            value_fields.append('twitter_handle')
        if 'former-names' in active_col_ids:
            value_fields.append('former_names')

        limit_param = get_params.get('limit', '').strip()
        limit = int(limit_param) if limit_param.isdigit() and int(limit_param) > 0 else None

        if order_by_raw:
            desc = order_by_raw[0] == '-'
            db_field = _ORDER_BY_MAP.get(order_col_key, 'name')
            order_by_expr = f'-{db_field}' if desc else db_field
            if order_col_key in _ORDER_BY_MAP and db_field != 'name':
                results = results.filter(**{f'{db_field}__isnull': False})
        else:
            order_by_expr = 'name'

        results.query.comment = "BROWSE-SEARCH"
        results = list(results.values(*value_fields).order_by(order_by_expr))
        if limit:
            results = results[:limit]
        num_results = len(results)

        # Feature column data — bulk fetch and merge (post-query)
        feature_cols = [c for c in active_columns if c.col_type == 'feature']
        if feature_cols:
            sv_ids = [r['id'] for r in results]
            feat_data = collections.defaultdict(lambda: collections.defaultdict(list))
            sf_qs = (
                SystemFeature.objects
                .filter(
                    version_id__in=sv_ids,
                    feature__slug__in=[c.col_id for c in feature_cols],
                )
                .select_related('feature', 'system')
                .prefetch_related('options')
            )
            for sf in sf_qs:
                for opt in sf.get_my_or_parent_options():
                    feat_data[sf.version_id][sf.feature.slug].append({
                        'value': opt.value,
                        'slug':  opt.slug,
                    })
            for r in results:
                for col in feature_cols:
                    key = 'col_' + col.col_id.replace('-', '_')
                    r[key] = feat_data[r['id']].get(col.col_id, [])

        # Build col_values list for each result (one entry per active column)
        for r in results:
            col_values = []
            for col in active_columns:
                if col.col_id == 'tags':
                    col_values.append({'type': 'tags', 'data': r['system_tags'] or []})
                elif col.col_id == 'start-year':
                    col_values.append({'type': 'year', 'data': r.get('start_year') or ''})
                elif col.col_id == 'end-year':
                    col_values.append({'type': 'year', 'data': r.get('end_year') or ''})
                elif col.col_type == 'feature':
                    key = 'col_' + col.col_id.replace('-', '_')
                    col_values.append({'type': 'feature_opts', 'data': r.get(key) or []})
                elif col.col_type == 'attribute':
                    key = 'col_' + col.col_id.replace('-', '_')
                    col_values.append({'type': 'attr_opts', 'data': r.get(key) or []})
                elif col.col_id == 'developer-orgs':
                    col_values.append({'type': 'orgs', 'data': r.get('col_developer_orgs') or []})
                elif col.col_id == 'acquired-by':
                    col_values.append({'type': 'orgs', 'data': r.get('col_acquired_by') or []})
                elif col.col_type == 'relationship':
                    key = 'col_' + col.col_id.replace('-', '_')
                    col_values.append({'type': 'systems', 'data': r.get(key) or []})
                elif col.col_id == 'country':
                    codes = [c for c in (r.get('countries') or '').split(',') if c]
                    country_data = [
                        {'code': c, 'name': CountryObj(c).name, 'flag_css': CountryObj(c).flag_css}
                        for c in codes if c
                    ]
                    col_values.append({'type': 'countries', 'data': country_data})
                elif col.col_id in _URL_COL_FIELDS:
                    key = 'col_' + col.col_id.replace('-', '_')
                    col_values.append({'type': 'url', 'data': r.get(key) or ''})
                elif col.col_id == 'twitter-handle':
                    col_values.append({'type': 'twitter', 'data': r.get('twitter_handle') or ''})
                elif col.col_id == 'former-names':
                    names = r.get('former_names') or []
                    col_values.append({'type': 'former-names', 'data': ', '.join(names)})
            r['col_values'] = col_values

        has_results = len(results) > 0
        suggestion = None
        if search_q and not has_results:
            suggestion = self.do_dym(search_q)

        # get year ranges
        years_start = SystemVersion.objects.filter(is_current=True, start_year__gt=0).aggregate(
            min_start_year=Min('start_year'), max_start_year=Max('start_year')
        )
        years_end = SystemVersion.objects.filter(is_current=True, end_year__gt=0).aggregate(
            min_end_year=Min('end_year'), max_end_year=Max('end_year')
        )
        years = {**years_start, **years_end}

        # Resolve SavedSearch from signed 'ss' token
        saved_search = None
        ss_token = get_params.get('ss', '').strip()
        if ss_token:
            pk = ss_decode(ss_token)
            if pk is not None:
                saved_search = SavedSearch.objects.filter(pk=pk).first()
                if saved_search:
                    title = saved_search.name

        show_all_url = None
        if limit:
            qs = urllib.parse.urlencode(
                [(k, v) for k in get_params.keys() if k != 'limit'
                 for v in get_params.getlist(k)]
            )
            show_all_url = ('?' + qs) if qs else '?'

        filter_groups = self.build_filter_groups(get_params)
        dropdown_fields = sorted(
            ['Start Year', 'End Year'] + [fg.label for fg in filter_groups],
            key=str.casefold,
        )
        return render(request, self.template_name, {
            'title': title,
            'activate': 'browse',
            'page_error': search_error or (_doi_warning_html(search_q) if _is_doi_query(search_q) else None),
            'filtergroups': filter_groups,
            'filtergroupsjson': [asdict(fg) for fg in filter_groups],
            'has_results': has_results,
            'query': search_q,
            'results': results,
            'num_results': num_results,
            'years': years,
            'has_search': len(search_keys) != 0,
            'search': search_keys,
            'suggestion': suggestion,
            'search_op': "and" if search_op == and_ else "or",
            'active_columns': active_columns,
            'active_col_ids': active_col_ids,
            'cols_are_custom': cols_are_custom,
            'available_builtin':    sorted((c for c in available_columns if c.col_type == 'builtin'), key=lambda c: c.label),
            'available_features':   [c for c in available_columns if c.col_type == 'feature'],
            'available_attributes': sorted((c for c in available_columns if c.col_type in ('attribute', 'relationship')), key=lambda c: c.label),
            'cols_param': ','.join(active_col_ids),
            'saved_search': saved_search,
            'dropdown_fields': dropdown_fields,
            'limit': limit,
            'show_all_url': show_all_url,
        })

    def handle_old_urls(self, request):
        query = []

        # get mapping of feature options
        featuresoptions_map = {
            str(fo_id): (f_slug, fo_slug)
            for fo_id,fo_slug,f_slug in FeatureOption.objects.all().order_by().values_list('id','slug','feature__slug')
        }

        for k in request.GET.keys():
            for v in request.GET.getlist(k):
                if k.startswith('fg'):
                    query.append( featuresoptions_map[v] )
                    pass
                elif v:
                    query.append((k,v))
                    pass
                pass
            pass

        return redirect( request.path + '?' + urllib.parse.urlencode(query) )


    pass