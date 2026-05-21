# django imports
import os
import tempfile

from cairosvg import svg2png
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

from dbdb.core.models import SystemVersion


def create_twitter_card(ver : SystemVersion):

    # Create a nicely formatted version of the logo for the twitter card
    template = os.path.join(settings.BASE_DIR, "static", settings.TWITTER_CARD_TEMPLATE)
    im1 = Image.open(template).convert("RGBA")
    new_im = Image.new('RGBA', (im1.width, im1.height))
    new_im.paste(im1, (0, 0))

    # If there is no logo, then we will create an image of just the name
    if not ver.logo:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 128)
        name = ver.system.name
        ascent, descent = font.getmetrics()
        # [width, height]
        text_size = (font.getmask(name).getbbox()[2], font.getmask(name).getbbox()[3] + descent)
        # text_size = font.getbbox(name)
        if name.find(" ") != -1:
            name = name.replace(" ", "\n")
            # Compute dimension of each line
            text_size = [0, 0]
            for line in name.split("\n"):
                width = font.getmask(line).getbbox()[2]
                height = font.getmask(line).getbbox()[3] + descent
                text_size[0] = max(text_size[0], width)
                text_size[1] += height + 5

        logo = Image.new('RGBA', text_size)
        text_draw = ImageDraw.Draw(logo)
        text_draw.text((0, 0), name, font=font, fill=(70, 70, 70, 255))

    # SVG
    elif ver.logo.path.lower().endswith("svg"):
        temp_name = os.path.join(tempfile.gettempdir(), next(tempfile._get_candidate_names()) + ".png")
        with open(ver.logo.path) as fd:
            svg2png(bytestring=fd.read(), write_to=temp_name, scale=3)
        logo = Image.open(temp_name).convert("RGBA")

    # PNG
    else:
        logo = Image.open(ver.logo).convert("RGBA")

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

    # Resize the mofo
    logo = logo.resize(new_size, Image.Resampling.LANCZOS)

    # Figure out the center of the white part of the card
    # Assume that the origin is (0,0). We will adjust by the base offset later
    offset = (settings.TWITTER_CARD_BASE_OFFSET_X + settings.TWITTER_CARD_MARGIN + (
                settings.TWITTER_CARD_MAX_WIDTH - logo.width) // 2, \
              settings.TWITTER_CARD_MARGIN + (settings.TWITTER_CARD_MAX_HEIGHT - logo.height) // 2)

    new_im.paste(logo, offset, logo)
    card_img = os.path.join(settings.TWITTER_CARD_ROOT, ver.get_twitter_card_image())
    new_im.save(card_img)
    return card_img