# django imports
import os
import tempfile
from io import BytesIO

from cairosvg import svg2png
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

from dbdb.core.models import SystemVersion


def create_twitter_card(ver : SystemVersion):

    # Load SVG template and convert to RGBA image
    with open(settings.TWITTER_CARD_TEMPLATE, 'rb') as f:
        png_bytes = svg2png(bytestring=f.read())
    im1 = Image.open(BytesIO(png_bytes)).convert("RGBA")
    new_im = Image.new('RGBA', (im1.width, im1.height))
    new_im.paste(im1, (0, 0))

    is_text = False

    # If there is no logo, then we will create an image of just the name
    if not ver.logo:
        is_text = True
        name = ver.system.name
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

    # SVG
    elif ver.logo.path.lower().endswith("svg"):
        temp_name = os.path.join(tempfile.gettempdir(), next(tempfile._get_candidate_names()) + ".png")
        with open(ver.logo.path) as fd:
            svg2png(bytestring=fd.read(), write_to=temp_name, scale=3, unsafe=True)
        logo = Image.open(temp_name).convert("RGBA")

    # PNG
    else:
        logo = Image.open(ver.logo).convert("RGBA")

    if not is_text:
        new_size = (0, 0)
        if logo.width > logo.height:
            ratio = (settings.TWITTER_CARD_MAX_WIDTH / float(logo.size[0]))
            new_size = (settings.TWITTER_CARD_MAX_WIDTH, int(float(logo.size[1]) * float(ratio)))
        else:
            ratio = (settings.TWITTER_CARD_MAX_HEIGHT / float(logo.size[1]))
            new_size = (int(float(logo.size[0]) * float(ratio)), settings.TWITTER_CARD_MAX_HEIGHT)

        # Check if either the new width or height exceed the max dimensions
        # We have to do this because the dimensions are not square
        if new_size[0] > settings.TWITTER_CARD_MAX_WIDTH:
            ratio = (settings.TWITTER_CARD_MAX_WIDTH / float(new_size[0]))
            new_size = (settings.TWITTER_CARD_MAX_WIDTH, int(float(new_size[1]) * float(ratio)))
        elif new_size[1] > settings.TWITTER_CARD_MAX_HEIGHT:
            ratio = (settings.TWITTER_CARD_MAX_HEIGHT / float(new_size[1]))
            new_size = (int(float(new_size[0]) * float(ratio)), settings.TWITTER_CARD_MAX_HEIGHT)

        logo = logo.resize(new_size, Image.Resampling.LANCZOS)

    # Center the logo in the right panel (which starts at TWITTER_CARD_BASE_OFFSET_X)
    content_width = new_im.width - settings.TWITTER_CARD_BASE_OFFSET_X
    offset = (
        settings.TWITTER_CARD_BASE_OFFSET_X + (content_width - logo.width) // 2,
        (new_im.height - logo.height) // 2,
    )

    if not os.path.exists(settings.TWITTER_CARD_ROOT):
        os.makedirs(settings.TWITTER_CARD_ROOT)
    card_img = os.path.join(settings.TWITTER_CARD_ROOT, ver.get_twitter_card_image())

    new_im.paste(logo, offset, logo)
    new_im.save(card_img)
    return card_img