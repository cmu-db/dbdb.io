from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'dbdb.core'

    def ready(self):
        from django.db.models.signals import m2m_changed, pre_save, post_save
        from dbdb.core.signals import developer_orgs_changed, _org_capture_logo, _org_regen_card_on_logo_change
        from dbdb.core.models import Organization, SystemVersion
        m2m_changed.connect(developer_orgs_changed, sender=SystemVersion.developer_orgs.through)
        pre_save.connect(_org_capture_logo, sender=Organization)
        post_save.connect(_org_regen_card_on_logo_change, sender=Organization)