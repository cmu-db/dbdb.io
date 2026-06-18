from django.test import SimpleTestCase

from dbdb.core.utils.citations import normalize_url


class NormalizeUrlUtmSourceTestCase(SimpleTestCase):

    def test_utm_source_is_stripped(self):
        url = "https://example.com/page?utm_source=newsletter"
        self.assertEqual(normalize_url(url), "https://example.com/page")

    def test_utm_source_stripped_alongside_other_params(self):
        url = "https://example.com/page?foo=bar&utm_source=twitter&baz=qux"
        result = normalize_url(url)
        self.assertNotIn("utm_source", result)
        self.assertIn("foo=bar", result)
        self.assertIn("baz=qux", result)

    def test_utm_source_case_insensitive(self):
        url = "https://example.com/page?UTM_SOURCE=google"
        self.assertNotIn("UTM_SOURCE", normalize_url(url))
        self.assertNotIn("utm_source", normalize_url(url))

    def test_url_without_utm_source_unchanged(self):
        url = "https://example.com/page?q=search&lang=en"
        result = normalize_url(url)
        self.assertIn("q=search", result)
        self.assertIn("lang=en", result)

    def test_url_with_only_utm_source_loses_query_string(self):
        url = "https://example.com/page?utm_source=email"
        self.assertEqual(normalize_url(url), "https://example.com/page")
