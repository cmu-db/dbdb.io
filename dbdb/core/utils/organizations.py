from __future__ import annotations

import difflib
import logging
import re

from django.db import connection, transaction

from dbdb.core.models import Acquisition, Organization

LOG = logging.getLogger(__name__)

# ── Fuzzy-matching helpers ────────────────────────────────────────────────────

_SUFFIX_WORDS: frozenset[str] = frozenset({
    # legal entity types
    'inc', 'incorporated', 'llc', 'ltd', 'limited', 'co', 'company',
    'corp', 'corporation', 'gmbh', 'ag', 'sa', 'plc', 'bv', 'nv', 'se', 'lp',
    # product / org type words
    'software', 'technologies', 'technology', 'tech', 'systems', 'system',
    'group', 'foundation', 'labs', 'lab', 'laboratory', 'laboratories',
    'international', 'holdings', 'solutions', 'services', 'enterprises',
    'ventures', 'partners', 'partnership', 'associates', 'consulting',
    'research', 'institute', 'network', 'networks', 'media',
})


def _normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^\w\s]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def _strip_suffixes(tokens: list[str]) -> list[str]:
    while tokens and tokens[-1] in _SUFFIX_WORDS:
        tokens = tokens[:-1]
    return tokens


def _get_acronym(name: str) -> str | None:
    """Extract a parenthetical acronym, e.g. '(CNCF)' → 'cncf'."""
    m = re.search(r'\(([A-Za-z]{2,})\)', name)
    return m.group(1).lower() if m else None


def _initials(tokens: list[str]) -> str:
    return ''.join(t[0] for t in tokens if t)


def _words_prefix_match(ta: list[str], tb: list[str]) -> bool:
    """True if every word pair matches exactly or one is a prefix of the other (min 3 chars)."""
    if len(ta) != len(tb):
        return False
    for a, b in zip(ta, tb):
        if a == b:
            continue
        short, long_ = (a, b) if len(a) <= len(b) else (b, a)
        if len(short) >= 3 and long_.startswith(short):
            continue
        return False
    return True


def _match_reason(
    name: str, norm: str, tokens: list[str], core: list[str],
    acronym: str | None, initials: str,
    other: Organization,
) -> str | None:
    o_norm    = _normalize(other.name)
    o_tokens  = o_norm.split()
    o_core    = _strip_suffixes(list(o_tokens))
    o_acronym = _get_acronym(other.name)
    o_initials = _initials(o_tokens)

    if norm == o_norm:
        return None

    # 1. Suffix-stripped cores match (covers Inc/Incorporated/bare-name variants)
    if core and o_core and core == o_core:
        return "suffix variant"

    # 2. Parenthetical acronym matches initials of the other name
    if acronym and acronym == o_initials and len(o_tokens) >= 3:
        return "acronym expansion"
    if o_acronym and o_acronym == initials and len(tokens) >= 3:
        return "acronym expansion"

    # 3. One name IS the other's initials (e.g. "CNCF" vs full name)
    if len(tokens) == 1 and norm == o_initials and len(o_tokens) >= 3:
        return "abbreviation"
    if len(o_tokens) == 1 and o_norm == initials and len(tokens) >= 3:
        return "abbreviation"

    # 4. Word-level prefix match — catches name variations (Jeff/Jeffrey, etc.)
    if len(tokens) >= 2 and _words_prefix_match(tokens, o_tokens):
        return "name variation"

    # 5. High character-level similarity — catches single-letter typos
    min_len = min(len(norm), len(o_norm))
    if min_len >= 6:
        ratio = difflib.SequenceMatcher(None, norm, o_norm).ratio()
        threshold = 0.90 if min_len <= 10 else 0.85
        if ratio >= threshold:
            return f"similar spelling ({ratio:.0%})"

    return None


def find_potential_matches(
    org: Organization,
    queryset=None,
) -> list[tuple[Organization, str]]:
    """
    Find Organizations whose names are likely duplicates of *org*.

    Returns a list of (other_org, reason) sorted by name. Reasons:
      - "suffix variant"   : same core name, different legal suffix
      - "acronym expansion": one name has a parenthetical acronym matching
                             the initials of the other
      - "abbreviation"     : one name IS the initials of the other
      - "name variation"   : word-level prefix match (e.g. Jeff/Jeffrey)
      - "similar spelling" : high character similarity (likely typo)
    """
    if queryset is None:
        queryset = Organization.objects.exclude(id=org.id)

    norm     = _normalize(org.name)
    tokens   = norm.split()
    core     = _strip_suffixes(list(tokens))
    acronym  = _get_acronym(org.name)
    initials = _initials(tokens)

    results: list[tuple[Organization, str]] = []
    for other in queryset:
        reason = _match_reason(
            org.name, norm, tokens, core, acronym, initials, other
        )
        if reason:
            results.append((other, reason))

    results.sort(key=lambda x: x[0].name.lower())
    return results


def merge_organizations(merge_to: Organization, merge_from: list[Organization]) -> Organization:
    """
    Merge all references to each Organization in *merge_from* into *merge_to*,
    then delete the now-unreferenced merge_from rows.

    Handles:
      - M2M through-table: core_systemversion_developer_orgs
      - FK on Acquisition.organization (unique_together with version — deduplicated)
    """
    LOG.debug("Merging %d organization(s) into '%s'", len(merge_from), merge_to)

    from_ids = [o.id for o in merge_from]
    all_ids  = from_ids + [merge_to.id]

    with transaction.atomic():
        # ── M2M: core_systemversion_developer_orgs ────────────────────────
        table     = "core_systemversion_developer_orgs"
        owner_col = "systemversion_id"
        fk_col    = "organization_id"

        with connection.cursor() as cursor:
            placeholders = ", ".join(["%s"] * len(all_ids))
            cursor.execute(
                f"SELECT id, {owner_col}, {fk_col} "
                f"FROM {table} WHERE {fk_col} IN ({placeholders})",
                all_ids,
            )
            rows = cursor.fetchall()

            keep_pairs: set[tuple[int, int]] = {
                (row[1], row[2]) for row in rows if row[2] == merge_to.id
            }
            to_update: list[tuple[int, int]] = []
            to_delete: list[tuple[int, int]] = []

            for _row_id, owner_id, org_id in rows:
                if org_id == merge_to.id:
                    continue
                if (owner_id, merge_to.id) in keep_pairs:
                    to_delete.append((owner_id, org_id))
                else:
                    to_update.append((owner_id, org_id))
                    keep_pairs.add((owner_id, merge_to.id))

            for owner_id, org_id in to_update:
                cursor.execute(
                    f"UPDATE {table} SET {fk_col} = %s "
                    f"WHERE {fk_col} = %s AND {owner_col} = %s",
                    [merge_to.id, org_id, owner_id],
                )
                LOG.info("Updated %d row(s) in %s", cursor.rowcount, table)

            for owner_id, org_id in to_delete:
                cursor.execute(
                    f"DELETE FROM {table} WHERE {fk_col} = %s AND {owner_col} = %s",
                    [org_id, owner_id],
                )
                LOG.info("Deleted %d row(s) in %s", cursor.rowcount, table)

        # ── FK: Acquisition.organization (unique_together with version) ───
        for org in merge_from:
            for acq in list(Acquisition.objects.filter(organization=org)):
                if Acquisition.objects.filter(version=acq.version, organization=merge_to).exists():
                    acq.delete()
                    LOG.info(
                        "Deleted duplicate Acquisition(version=%d, org=%s)",
                        acq.version_id, org.name,
                    )
                else:
                    acq.organization = merge_to
                    acq.save(update_fields=["organization"])
                    LOG.info(
                        "Reassigned Acquisition(version=%d) from %s to %s",
                        acq.version_id, org.name, merge_to.name,
                    )

        # ── Delete the now-unreferenced source organizations ──────────────
        deleted, _ = Organization.objects.filter(id__in=from_ids).delete()
        LOG.info("Deleted %d Organization(s): %s", deleted, from_ids)

    return merge_to
