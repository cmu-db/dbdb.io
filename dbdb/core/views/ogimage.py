import json
from io import BytesIO

from cairosvg import svg2png
from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control
from PIL import Image, ImageDraw, ImageFont

_TEXT_COLOR   = (26, 26, 23, 255)
_COUNT_COLOR  = (130, 130, 127, 255)
_QUERY_FONT_MAX = 120
_COUNT_FONT_RATIO = 0.38
_LINE_GAP = 64
_LINE_SPACING = 4
_ICON_SIZE = 100

# Lazy-loaded FA icon data — loaded on first use so a missing setting or file
# at import time does not permanently break icon rendering.
_FA_ICONS_CACHE = None


def _fa_icons():
    global _FA_ICONS_CACHE
    if _FA_ICONS_CACHE is None:
        try:
            with open(settings.TWITTER_CARD_FA_ICONS_JSON) as f:
                _FA_ICONS_CACHE = json.load(f)
        except Exception:
            return {}
    return _FA_ICONS_CACHE


def _render_fa_icon(fa_class, size_px, color=_TEXT_COLOR[:3]):
    """Render an FA icon class string to a PIL RGBA Image, or return None."""
    parts = fa_class.split()
    style = 'regular' if parts and parts[0] == 'far' else \
            'brands'  if parts and parts[0] == 'fab' else 'solid'
    icon_name = next((p[3:] for p in parts if p.startswith('fa-')), None)
    if not icon_name:
        return None
    svg_styles = _fa_icons().get(icon_name, {}).get('svg', {})
    svg_entry = svg_styles.get(style) or next(iter(svg_styles.values()), None)
    if not svg_entry:
        return None
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
            return font, lines
    font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, 18)
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
        if n != 1: label += 's'
        return f'{n:,} {label} Found'
    except ValueError:
        return ''


@method_decorator(cache_control(public=True, max_age=3600), name='dispatch')
class OGImageSearchView(View):

    def get(self, request):
        q = request.GET.get('q', '').strip()
        n_str = request.GET.get('n', '').strip()

        im = _load_template_image()
        draw = ImageDraw.Draw(im)
        panel_w, panel_cx = _panel_geometry(im)

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

        title_h = _text_block_height(font, lines)
        total_h = title_h + (_LINE_GAP + c_h if count_text else 0)
        y = (im.height - total_h) // 2

        y = _draw_text_block(draw, font, lines, panel_cx, y, _TEXT_COLOR)

        if count_text and count_font:
            draw.text(
                (panel_cx - c_w // 2, y + _LINE_GAP),
                count_text, font=count_font, fill=_COUNT_COLOR,
            )

        buf = BytesIO()
        im.save(buf, format='PNG')
        return HttpResponse(buf.getvalue(), content_type='image/png')


@method_decorator(cache_control(public=True, max_age=3600), name='dispatch')
class OGImageSavedSearchView(View):

    def get(self, request, pk):
        from dbdb.core.models import SavedSearch
        try:
            ss = SavedSearch.objects.get(pk=pk)
        except SavedSearch.DoesNotExist:
            raise Http404

        n_str = request.GET.get('n', '').strip()

        im = _load_template_image()
        draw = ImageDraw.Draw(im)
        panel_w, panel_cx = _panel_geometry(im)

        # FA icon rendered from SVG path data
        icon_img = _render_fa_icon(ss.icon, _ICON_SIZE) if ss.icon else None

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

        icon_h = icon_img.height if icon_img else 0
        title_h = _text_block_height(font, lines)
        total_h = (
            (icon_h + _LINE_GAP if icon_img else 0)
            + title_h
            + (_LINE_GAP + c_h if count_text else 0)
        )
        y = (im.height - total_h) // 2

        if icon_img:
            im.paste(icon_img, (panel_cx - icon_img.width // 2, y), icon_img)
            y += icon_h + _LINE_GAP

        y = _draw_text_block(draw, font, lines, panel_cx, y, _TEXT_COLOR)

        if count_text and count_font:
            draw.text((panel_cx - c_w // 2, y + _LINE_GAP), count_text, font=count_font, fill=_COUNT_COLOR)

        buf = BytesIO()
        im.save(buf, format='PNG')
        return HttpResponse(buf.getvalue(), content_type='image/png')
