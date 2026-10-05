from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from dbdb.core.models import CitationUrl


class CitationUrlAdminStatusActionTestCase(TestCase):

    fixtures = ['adminuser.json']

    def setUp(self):
        self.client.force_login(User.objects.get(username='admin'))
        self.url = reverse('admin:core_citationurl_changelist')
        self.c1 = CitationUrl.objects.create(url='https://wutang.example.com/rza', status=CitationUrl.Status.VALID)
        self.c2 = CitationUrl.objects.create(url='https://wutang.example.com/gza', status=CitationUrl.Status.UNKNOWN)
        self.c3 = CitationUrl.objects.create(url='https://wutang.example.com/odb', status=CitationUrl.Status.VALID)

    def test_changelist_lists_all_status_actions(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        for m in CitationUrl.Status:
            self.assertContains(resp, f'value="set_status_{m.name.lower()}"')

    def test_set_status_updates_only_selected(self):
        resp = self.client.post(self.url, {
            'action': 'set_status_dead',
            '_selected_action': [self.c1.pk, self.c2.pk],
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Set status &#x27;Dead&#x27; on 2 citation URL(s).")

        for c in (self.c1, self.c2, self.c3):
            c.refresh_from_db()
        self.assertEqual(self.c1.status, CitationUrl.Status.DEAD)
        self.assertEqual(self.c2.status, CitationUrl.Status.DEAD)
        self.assertEqual(self.c3.status, CitationUrl.Status.VALID)
