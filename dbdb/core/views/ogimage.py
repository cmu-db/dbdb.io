from io import BytesIO

from cairosvg import svg2png
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control
from PIL import Image, ImageDraw, ImageFont

_TEXT_COLOR = (26, 26, 23, 255)
_QUERY_FONT_MAX = 96
_COUNT_FONT_RATIO = 0.42
_LINE_GAP = 28


@method_decorator(cache_control(public=True, max_age=3600), name='dispatch')
class OGImageSearchView(View):

    def get(self, request):
        q = request.GET.get('q', '').strip()
        n = request.GET.get('n', '').strip()

        with open(settings.TWITTER_CARD_TEMPLATE, 'rb') as f:
            png_bytes = svg2png(bytestring=f.read())
        im = Image.open(BytesIO(png_bytes)).convert('RGBA')
        draw = ImageDraw.Draw(im)

        margin   = settings.TWITTER_CARD_MARGIN
        offset_x = settings.TWITTER_CARD_BASE_OFFSET_X
        panel_w  = im.width - offset_x - 2 * margin
        panel_cx = offset_x + (im.width - offset_x) // 2

        query_text = f'"{q}"' if q else settings.DBDB_SITE_NAME
        font_size = _QUERY_FONT_MAX
        while font_size > 18:
            font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, font_size)
            if font.getmask(query_text).getbbox()[2] <= panel_w:
                break
            font_size -= 8
        q_w = font.getmask(query_text).getbbox()[2]
        q_h = font.getmask(query_text).getbbox()[3]

        count_text = ''
        c_w = c_h = 0
        count_font = None
        if n:
            try:
                count_int = int(n)
                label = 'System' if count_int == 1 else 'Systems'
                count_text = f'{count_int:,} {label} Found'
            except ValueError:
                pass
        if count_text:
            count_font_size = max(24, int(font_size * _COUNT_FONT_RATIO))
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
