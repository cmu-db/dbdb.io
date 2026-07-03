from django.test import TestCase
from PIL import Image

from dbdb.core.views.ogimage import _render_fa_icon


class FAIconRenderingTestCase(TestCase):
    """
    Regression tests for _render_fa_icon.

    The bug: 'fa-solid fa-building-columns' caused _render_fa_icon to pick up
    'fa-solid' as the icon name (icon_name='solid') because the old code used
    `next(p[3:] for p in parts if p.startswith('fa-'))` which matches the style
    prefix before the actual icon name. The fix skips known style tokens.
    """

    def _assert_renders(self, fa_class, size=64):
        img = _render_fa_icon(fa_class, size)
        self.assertIsNotNone(img, f"_render_fa_icon returned None for {fa_class!r}")
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (size, size))

    def test_new_format_solid_icon(self):
        self._assert_renders('fa-solid fa-robot')

    def test_new_format_solid_icon_was_returning_wrong_name(self):
        # Regression: 'fa-solid fa-building-columns' previously extracted
        # icon_name='solid' (from 'fa-solid') instead of 'building-columns'.
        self._assert_renders('fa-solid fa-building-columns')

    def test_new_format_brands_icon(self):
        self._assert_renders('fa-brands fa-aws')

    def test_new_format_brands_style_detected(self):
        # 'fa-brands' was not recognised, so style defaulted to 'solid' and the
        # icon lookup fell back to solid even for brand-only icons.
        self._assert_renders('fa-brands fa-google')

    def test_legacy_format_solid_icon(self):
        self._assert_renders('fas fa-handshake')

    def test_returns_none_for_unknown_icon(self):
        img = _render_fa_icon('fa-solid fa-does-not-exist-xyzzy', 64)
        self.assertIsNone(img)

    def test_returns_none_for_empty_string(self):
        img = _render_fa_icon('', 64)
        self.assertIsNone(img)
