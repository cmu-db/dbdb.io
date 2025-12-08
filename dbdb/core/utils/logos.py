import io
import xml.etree.ElementTree as ET

from PIL import Image
from collections import Counter
from typing import Tuple, Union

def extract_dimensions(path: str) -> tuple[int, int]:
    """
    Return (width, height) of an image.
    Supports JPG, PNG, GIF, and SVG.
    """

    # --- SVG ---
    if path.lower().endswith(".svg"):
        tree = ET.parse(path)
        root = tree.getroot()

        # SVG width/height may include units (like "100px")
        def parse_dim(value):
            if value is None:
                return None
            value = value.strip()
            # strip "px" or other units
            num = "".join(c for c in value if (c.isdigit() or c == "."))
            return float(num) if num else None

        w = parse_dim(root.get("width"))
        h = parse_dim(root.get("height"))

        # If width/height not explicitly set, check viewBox
        if (w is None or h is None) and root.get("viewBox"):
            _, _, vb_w, vb_h = map(float, root.get("viewBox").split())
            w = w or vb_w
            h = h or vb_h

        if w is None or h is None:
            raise ValueError("Unable to determine SVG dimensions.")

        return int(w), int(h)

    # --- Raster (JPG/PNG/GIF/etc.) ---
    with Image.open(path) as img:
        return img.width, img.height

def extract_color(image_path: str, exclude_dark: bool = True,
                  min_saturation: int = 20, top_n: int = 10) -> Tuple[int, int, int]:
    """
    Extract the most prominent color from an image (logo).

    Args:
        image_path: Path to the image file (JPG, PNG, SVG, etc.)
        exclude_dark: If True, excludes very dark colors (like black text)
        min_saturation: Minimum saturation threshold (0-255) to filter out grays/blacks
        top_n: Number of top colors to consider

    Returns:
        Tuple of (R, G, B) representing the most prominent color
    """

    # Handle SVG files by converting to PNG first
    if image_path.lower().endswith('.svg'):
        try:
            import cairosvg
            png_data = cairosvg.svg2png(url=image_path)
            img = Image.open(io.BytesIO(png_data))
        except ImportError:
            raise ImportError("cairosvg is required for SVG support. Install with: pip install cairosvg")
    else:
        img = Image.open(image_path)

    # Convert to RGB if necessary (handles RGBA, P, etc.)
    if img.mode != 'RGB':
        # For images with transparency, paste on white background
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        else:
            img = img.convert('RGB')

    # Resize for faster processing (maintain aspect ratio)
    img.thumbnail((200, 200))

    # Get all pixels
    pixels = list(img.getdata())

    # Filter out colors based on criteria
    filtered_pixels = []
    for r, g, b in pixels:
        # Skip white and near-white pixels (common backgrounds)
        if r > 240 and g > 240 and b > 240:
            continue

        # Calculate saturation to filter out black/gray text
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = 0 if max_val == 0 else (max_val - min_val) / max_val * 255

        if exclude_dark:
            # Exclude very dark colors (likely text)
            brightness = (r + g + b) / 3
            if brightness < 50:  # Very dark
                continue

            # Exclude low saturation colors (grays, blacks)
            if saturation < min_saturation:
                continue

        filtered_pixels.append((r, g, b))

    # If we filtered everything out, fall back to original pixels (excluding white)
    if not filtered_pixels:
        filtered_pixels = [(r, g, b) for r, g, b in pixels
                          if not (r > 240 and g > 240 and b > 240)]

    # If still empty, return a default color
    if not filtered_pixels:
        return (100, 100, 100)

    # Count color frequencies
    color_counts = Counter(filtered_pixels)

    # Get top N most common colors
    top_colors = color_counts.most_common(top_n)

    # From top colors, pick the one with highest saturation
    # This helps select vibrant brand colors over muted ones
    best_color = None
    best_score = -1

    for color, count in top_colors:
        r, g, b = color
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = 0 if max_val == 0 else (max_val - min_val) / max_val

        # Score based on both frequency and saturation
        score = count * (1 + saturation)

        if score > best_score:
            best_score = score
            best_color = color

    return best_color if best_color else top_colors[0][0]


def color_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color string."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)
