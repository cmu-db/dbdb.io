# stdlib imports
import os
import re
from io import BytesIO

from cairosvg import svg2png
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


def create_twitter_card(obj):
    """Generate a Twitter card PNG for obj.

    obj must implement:
      - obj.logo          — ThumbnailerField (may be blank)
      - obj.get_twitter_card_name()  → str
      - obj.get_twitter_card_image() → relative path like "db/slug.png"
    """

    # Load SVG template and convert to RGBA image
    with open(settings.TWITTER_CARD_TEMPLATE, 'rb') as f:
        png_bytes = svg2png(bytestring=f.read())
    im1 = Image.open(BytesIO(png_bytes)).convert("RGBA")
    new_im = Image.new('RGBA', (im1.width, im1.height))
    new_im.paste(im1, (0, 0))

    is_text = False

    # If there is no logo, create an image of just the name
    if not obj.logo:
        is_text = True
        name = obj.get_twitter_card_name()
        lines = name.split() if " " in name else [name]
        display_name = "\n".join(lines)

        # Shrink font until the widest line fits within the right panel
        max_text_width = new_im.width - settings.TWITTER_CARD_BASE_OFFSET_X - 2 * settings.TWITTER_CARD_MARGIN
        font_size = 512
        while font_size > 12:
            font = ImageFont.truetype(settings.TWITTER_CARD_FONT_PATH, font_size)
            if max(font.getmask(line).getbbox()[2] for line in lines) <= max_text_width:
                break
            font_size -= 8

        ascent, descent = font.getmetrics()
        text_size = [0, 0]
        for line in lines:
            text_size[0] = max(text_size[0], font.getmask(line).getbbox()[2])
            text_size[1] += font.getmask(line).getbbox()[3] + descent + 5

        logo = Image.new('RGBA', text_size)
        text_draw = ImageDraw.Draw(logo)
        text_draw.text((0, 0), display_name, font=font, fill=(26, 26, 23, 255))

    # SVG logo — rasterize at the panel dimensions so PIL only ever scales down
    elif obj.logo.path.lower().endswith("svg"):
        panel_w = new_im.width - settings.TWITTER_CARD_BASE_OFFSET_X - 2 * settings.TWITTER_CARD_MARGIN
        panel_h = new_im.height - 2 * settings.TWITTER_CARD_MARGIN
        with open(obj.logo.path) as fd:
            svg_content = fd.read()
        # cairosvg chokes on attribute values of literal "null" (e.g. stroke-opacity="null")
        svg_content = re.sub(r' [\w:-]+="null"', '', svg_content)
        png_bytes = svg2png(bytestring=svg_content.encode(), output_width=panel_w, output_height=panel_h, unsafe=True)
        logo = Image.open(BytesIO(png_bytes)).convert("RGBA")

    # PNG logo
    else:
        logo = Image.open(obj.logo).convert("RGBA")

    if not is_text:
        max_w = new_im.width - settings.TWITTER_CARD_BASE_OFFSET_X - 2 * settings.TWITTER_CARD_MARGIN
        max_h = new_im.height - 2 * settings.TWITTER_CARD_MARGIN

        if logo.width > logo.height:
            ratio = max_w / float(logo.size[0])
            new_size = (max_w, int(logo.size[1] * ratio))
        else:
            ratio = max_h / float(logo.size[1])
            new_size = (int(logo.size[0] * ratio), max_h)

        # Clamp whichever dimension still exceeds its bound after the first scale
        if new_size[0] > max_w:
            ratio = max_w / float(new_size[0])
            new_size = (max_w, int(new_size[1] * ratio))
        elif new_size[1] > max_h:
            ratio = max_h / float(new_size[1])
            new_size = (int(new_size[0] * ratio), max_h)

        logo = logo.resize(new_size, Image.Resampling.LANCZOS)

    # Center the logo in the right panel (which starts at TWITTER_CARD_BASE_OFFSET_X)
    content_width = new_im.width - settings.TWITTER_CARD_BASE_OFFSET_X
    offset = (
        settings.TWITTER_CARD_BASE_OFFSET_X + (content_width - logo.width) // 2,
        (new_im.height - logo.height) // 2,
    )

    card_rel = obj.get_twitter_card_image()
    card_img = os.path.join(settings.TWITTER_CARD_ROOT, card_rel)
    card_dir = os.path.dirname(card_img)
    os.makedirs(card_dir, mode=0o775, exist_ok=True)

    new_im.paste(logo, offset, logo)
    new_im.save(card_img)
    os.chmod(card_img, 0o664)
    return card_img
