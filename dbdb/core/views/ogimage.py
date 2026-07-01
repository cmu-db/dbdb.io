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
_QUERY_FONT_MAX = 96
_COUNT_FONT_RATIO = 0.42
_LINE_GAP = 28
_ICON_SIZE = 72


def _load_fa_icons():
    try:
        with open(settings.TWITTER_CARD_FA_ICONS_JSON) as f:
            return json.load(f)
    except Exception:
        return {}

_FA_ICONS_DATA = _load_fa_icons()


def _render_fa_icon(fa_class, size_px, color=_TEXT_COLOR[:3]):
    """Render an FA icon class string to a PIL RGBA Image, or return None."""
    parts = fa_class.split()
    style = 'regular' if parts and parts[0] == 'far' else \
            'brands'  if parts and parts[0] == 'fab' else 'solid'
    icon_name = next((p[3:] for p in parts if p.startswith('fa-')), None)
    if not icon_name:
        return None
    svg_styles = _FA_ICONS_DATA.get(icon_name, {}).get('svg', {})
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


def _render_text_line(text, max_w, start_size):
    """Return (font, text_w, text_h) with font shrunk to fit max_w."""
    font_size = start_size
    while font_size > 18:
        font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, font_size)
        if font.getmask(text).getbbox()[2] <= max_w:
            break
        font_size -= 8
    bbox = font.getmask(text).getbbox()
    return font, bbox[2], bbox[3]


def _count_text(n_str):
    """Parse n_str -> '4 Systems Found' string, or ''."""
    if not n_str:
        return ''
    try:
        n = int(n_str)
        label = 'System' if n == 1 else 'Systems'
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

        query_text = f'"{q}"' if q else settings.DBDB_SITE_NAME
        font, q_w, q_h = _render_text_line(query_text, panel_w, _QUERY_FONT_MAX)

        count_text = _count_text(n_str)
        c_w = c_h = 0
        count_font = None
        if count_text:
            count_font_size = max(24, int(font.size * _COUNT_FONT_RATIO))
            count_font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, count_font_size)
            c_w = count_font.getmask(count_text).getbbox()[2]
            c_h = count_font.getmask(count_text).getbbox()[3]

        total_h = q_h + (_LINE_GAP + c_h if count_text else 0)
        y0 = (im.height - total_h) // 2

        draw.text((panel_cx - q_w // 2, y0), query_text, font=font, fill=_TEXT_COLOR)
        if count_text and count_font:
            draw.text(
                (panel_cx - c_w // 2, y0 + q_h + _LINE_GAP),
                count_text, font=count_font, fill=_TEXT_COLOR,
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

        # Render FA icon from SVG (may be None if icon blank/unknown)
        icon_img = _render_fa_icon(ss.icon, _ICON_SIZE) if ss.icon else None

        # Name line
        name_font, name_w, name_h = _render_text_line(ss.name, panel_w, _QUERY_FONT_MAX)

        # Count line
        count_text = _count_text(n_str)
        c_w = c_h = 0
        count_font = None
        if count_text:
            count_font_size = max(24, int(name_font.size * _COUNT_FONT_RATIO))
            count_font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, count_font_size)
            c_w = count_font.getmask(count_text).getbbox()[2]
            c_h = count_font.getmask(count_text).getbbox()[3]

        # Stack: [icon?] + name + [count?]
        icon_h = icon_img.height if icon_img else 0
        total_h = (
            icon_h + (_LINE_GAP if icon_img else 0)
            + name_h
            + (_LINE_GAP + c_h if count_text else 0)
        )
        y = (im.height - total_h) // 2

        if icon_img:
            x_icon = panel_cx - icon_img.width // 2
            im.paste(icon_img, (x_icon, y), icon_img)
            y += icon_h + _LINE_GAP

        draw.text((panel_cx - name_w // 2, y), ss.name, font=name_font, fill=_TEXT_COLOR)
        y += name_h

        if count_text and count_font:
            draw.text((panel_cx - c_w // 2, y + _LINE_GAP), count_text, font=count_font, fill=_TEXT_COLOR)

        buf = BytesIO()
        im.save(buf, format='PNG')
        return HttpResponse(buf.getvalue(), content_type='image/png')
