import json
import logging
from io import BytesIO

from cairosvg import svg2png
from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control
from PIL import Image, ImageDraw, ImageFont

LOG = logging.getLogger(__name__)

_TEXT_COLOR   = (26, 26, 23, 255)   # RGBA — main title text (near-black)
_COUNT_COLOR  = (130, 130, 127, 255) # RGBA — "N Systems Found" subtitle (muted gray)
_QUERY_FONT_MAX = 120    # largest font size (px) tried when fitting title text
_COUNT_FONT_RATIO = 0.38 # subtitle font size as a fraction of the title font size
_LINE_GAP = 48           # vertical gap (px) between the title block and the count line
_ICON_GAP = 0            # vertical gap (px) between the FA icon and the title block
_LINE_SPACING = 4        # vertical gap (px) between wrapped title lines
_ICON_SIZE = 120         # FA icon render size (px); square

# Lazy-loaded FA icon data — loaded on first use so a missing setting or file
# at import time does not permanently break icon rendering.
_FA_ICONS_CACHE = None


def _fa_icons():
    global _FA_ICONS_CACHE
    if _FA_ICONS_CACHE is None:
        try:
            with open(settings.TWITTER_CARD_FA_ICONS_JSON) as f:
                _FA_ICONS_CACHE = json.load(f)
            LOG.debug('FA icons loaded: %d icons from %s', len(_FA_ICONS_CACHE), settings.TWITTER_CARD_FA_ICONS_JSON)
        except Exception:
            LOG.debug('FA icons failed to load from %s', settings.TWITTER_CARD_FA_ICONS_JSON, exc_info=True)
            return {}
    return _FA_ICONS_CACHE


def _render_fa_icon(fa_class, size_px, color=_TEXT_COLOR[:3]):
    """Render an FA icon class string to a PIL RGBA Image, or return None."""
    parts = fa_class.split()
    parts_set = set(parts)
    # Support both legacy (fas/far/fab) and current (fa-solid/fa-regular/fa-brands) prefixes
    _STYLE_TOKENS = {'fa-solid', 'fas', 'fa-regular', 'far', 'fa-brands', 'fab', 'fa'}
    if 'fa-regular' in parts_set or 'far' in parts_set:
        style = 'regular'
    elif 'fa-brands' in parts_set or 'fab' in parts_set:
        style = 'brands'
    else:
        style = 'solid'
    icon_name = next((p[3:] for p in parts if p.startswith('fa-') and p not in _STYLE_TOKENS), None)
    if not icon_name:
        LOG.debug('FA icon: no fa-* class found in %r', fa_class)
        return None
    svg_styles = _fa_icons().get(icon_name, {}).get('svg', {})
    svg_entry = svg_styles.get(style) or next(iter(svg_styles.values()), None)
    if not svg_entry:
        LOG.debug('FA icon: %r (style=%s) not found in icons data', icon_name, style)
        return None
    LOG.debug('FA icon: rendering %r style=%s at %dpx', icon_name, style, size_px)
    vb = ' '.join(str(v) for v in svg_entry['viewBox'])
    r, g, b = color
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">'
        f'<path fill="rgb({r},{g},{b})" d="{svg_entry["path"]}"/></svg>'
    )
    png = svg2png(bytestring=svg.encode(), output_width=size_px, output_height=size_px)
    return Image.open(BytesIO(png)).convert('RGBA')


def _load_template_image():
    """Load the SVG card template and return an RGBA PIL Image."""
    with open(settings.TWITTER_CARD_TEMPLATE, 'rb') as f:
        png_bytes = svg2png(bytestring=f.read())
    return Image.open(BytesIO(png_bytes)).convert('RGBA')


def _panel_geometry(im):
    """Return (panel_w, panel_cx) for the right content panel."""
    margin   = settings.TWITTER_CARD_MARGIN
    offset_x = settings.TWITTER_CARD_BASE_OFFSET_X
    panel_w  = im.width - offset_x - 2 * margin
    panel_cx = offset_x + (im.width - offset_x) // 2
    return panel_w, panel_cx


def _wrap_text(text, max_w, start_size, max_lines=3):
    """
    Return (font, lines) using the largest font size where the text wraps
    into at most max_lines lines, each fitting within max_w pixels.
    """
    words = text.split()
    for font_size in range(start_size, 17, -4):
        font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, font_size)
        lines = []
        current = ''
        for word in words:
            candidate = (current + ' ' + word).strip()
            if font.getmask(candidate).getbbox()[2] <= max_w:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= max_lines:
            LOG.debug('wrap_text: %r -> %d lines at %dpx font', text, len(lines), font_size)
            return font, lines
    font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, 18)
    LOG.debug('wrap_text: %r -> fallback 18px, 1 line', text)
    return font, [text]


def _text_block_height(font, lines):
    """Total pixel height of a block of lines rendered with the given font."""
    if not lines:
        return 0
    line_h = max(font.getmask(l).getbbox()[3] for l in lines)
    return line_h * len(lines) + _LINE_SPACING * (len(lines) - 1)


def _draw_text_block(draw, font, lines, panel_cx, y, color):
    """Draw centered multi-line text, returning the y position after the block."""
    line_h = max(font.getmask(l).getbbox()[3] for l in lines)
    for i, line in enumerate(lines):
        w = font.getmask(line).getbbox()[2]
        draw.text((panel_cx - w // 2, y), line, font=font, fill=color)
        if i < len(lines) - 1:
            y += line_h + _LINE_SPACING
    return y + line_h


def _count_text(n_str):
    """Parse n_str -> '4 Systems Found' string, or ''."""
    if not n_str:
        return ''
    try:
        n = int(n_str)
        label = 'Database System'
        if n != 1: label += 's '
        return f'{n:,} {label}'
    except ValueError:
        return ''


@method_decorator(cache_control(public=True, max_age=3600), name='dispatch')
class OGImageSearchView(View):

    def get(self, request):
        q = request.GET.get('q', '').strip()
        n_str = request.GET.get('n', '').strip()
        LOG.debug('OGImageSearchView: q=%r n=%r', q, n_str)

        im = _load_template_image()
        draw = ImageDraw.Draw(im)
        panel_w, panel_cx = _panel_geometry(im)
        LOG.debug('OGImageSearchView: canvas=%s panel_w=%d panel_cx=%d', im.size, panel_w, panel_cx)

        raw_text = f'"{q}"' if q else settings.DBDB_SITE_NAME
        font, lines = _wrap_text(raw_text, panel_w, _QUERY_FONT_MAX)

        count_text = _count_text(n_str)
        c_w = c_h = 0
        count_font = None
        if count_text:
            count_font_size = max(24, int(font.size * _COUNT_FONT_RATIO))
            count_font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, count_font_size)
            c_w = count_font.getmask(count_text).getbbox()[2]
            c_h = count_font.getmask(count_text).getbbox()[3]
            LOG.debug('OGImageSearchView: count=%r font_size=%d', count_text, count_font_size)

        title_h = _text_block_height(font, lines)
        total_h = title_h + (_LINE_GAP + c_h if count_text else 0)
        y = (im.height - total_h) // 2
        LOG.debug('OGImageSearchView: title_h=%d total_h=%d y_start=%d', title_h, total_h, y)

        y = _draw_text_block(draw, font, lines, panel_cx, y, _TEXT_COLOR)

        if count_text and count_font:
            draw.text(
                (panel_cx - c_w // 2, y + _LINE_GAP),
                count_text, font=count_font, fill=_COUNT_COLOR,
            )

        buf = BytesIO()
        im.save(buf, format='PNG')
        LOG.debug('OGImageSearchView: done, PNG size=%d bytes', len(buf.getvalue()))
        return HttpResponse(buf.getvalue(), content_type='image/png')


@method_decorator(cache_control(public=True, max_age=3600), name='dispatch')
class OGImageSavedSearchView(View):

    def get(self, request, pk):
        from dbdb.core.models import SavedSearch
        try:
            ss = SavedSearch.objects.get(pk=pk)
        except SavedSearch.DoesNotExist:
            LOG.debug('OGImageSavedSearchView: pk=%d not found', pk)
            raise Http404

        n_str = request.GET.get('n', '').strip()
        LOG.debug('OGImageSavedSearchView: pk=%d name=%r icon=%r n=%r', pk, ss.name, ss.icon, n_str)

        im = _load_template_image()
        draw = ImageDraw.Draw(im)
        panel_w, panel_cx = _panel_geometry(im)
        LOG.debug('OGImageSavedSearchView: canvas=%s panel_w=%d panel_cx=%d', im.size, panel_w, panel_cx)

        # FA icon rendered from SVG path data
        icon_img = _render_fa_icon(ss.icon, _ICON_SIZE) if ss.icon else None
        LOG.debug('OGImageSavedSearchView: icon_img=%s', icon_img.size if icon_img else None)

        # Name — wrapped to fill the panel width
        font, lines = _wrap_text(ss.name, panel_w, _QUERY_FONT_MAX)

        # Count line
        count_text = _count_text(n_str)
        c_w = c_h = 0
        count_font = None
        if count_text:
            count_font_size = max(24, int(font.size * _COUNT_FONT_RATIO))
            count_font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, count_font_size)
            c_w = count_font.getmask(count_text).getbbox()[2]
            c_h = count_font.getmask(count_text).getbbox()[3]
            LOG.debug('OGImageSavedSearchView: count=%r font_size=%d', count_text, count_font_size)

        icon_h = icon_img.height if icon_img else 0
        title_h = _text_block_height(font, lines)
        total_h = (
            (icon_h + _ICON_GAP if icon_img else 0)
            + title_h
            + (_LINE_GAP + c_h if count_text else 0)
        )
        y = (im.height - total_h) // 2
        LOG.debug('OGImageSavedSearchView: icon_h=%d title_h=%d total_h=%d y_start=%d', icon_h, title_h, total_h, y)

        if icon_img:
            im.paste(icon_img, (panel_cx - icon_img.width // 2, y), icon_img)
            y += icon_h + _ICON_GAP

        y = _draw_text_block(draw, font, lines, panel_cx, y, _TEXT_COLOR)

        if count_text and count_font:
            draw.text((panel_cx - c_w // 2, y + _LINE_GAP), count_text, font=count_font, fill=_COUNT_COLOR)

        buf = BytesIO()
        im.save(buf, format='PNG')
        LOG.debug('OGImageSavedSearchView: done, PNG size=%d bytes', len(buf.getvalue()))
        return HttpResponse(buf.getvalue(), content_type='image/png')
