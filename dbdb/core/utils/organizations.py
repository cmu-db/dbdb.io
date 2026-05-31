from __future__ import annotations

import logging

from django.db import connection, transaction

from dbdb.core.models import Acquisition, Organization

LOG = logging.getLogger(__name__)


def merge_organizations(merge_to: Organization, merge_from: list[Organization]) -> Organization:
    """
    Merge all references to each Organization in *merge_from* into *merge_to*,
    then delete the now-unreferenced merge_from rows.

    Handles:
      - M2M through-table: core_systemversion_developer_orgs
      - FK on Acquisition.organization (unique_together with version — deduplicated)
    """
    LOG.debug("Merging %d organization(s) into %s", len(merge_from), merge_to)

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
