from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'dbdb.core'

    def ready(self):
        from django.db.models.signals import m2m_changed
        from dbdb.core.signals import developer_orgs_changed
        from dbdb.core.models import SystemVersion
        m2m_changed.connect(developer_orgs_changed, sender=SystemVersion.developer_orgs.through)