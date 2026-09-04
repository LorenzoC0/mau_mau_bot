#!/usr/bin/env python3
"""Generate an original, Telegram-ready UNO Flip compatible card deck.

The artwork follows the dimensions and visual language of the classic assets
in this repository without copying Mattel's official UNO Flip card artwork.
"""

import argparse
import colorsys
import json
import io
import copy
import xml.etree.ElementTree as ET
from pathlib import Path
from shutil import copyfile

from PIL import Image, ImageDraw, ImageEnhance, ImageFont


IMAGES_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = IMAGES_DIR / "flip"
CLASSIC_DIR = IMAGES_DIR / "classic"
CLASSIC_COLORBLIND_DIR = IMAGES_DIR / "classic_colorblind"
OVERLAY_DIR = IMAGES_DIR / "colorblind_overlay"
SIZE = (340, 512)

LIGHT_COLORS = {
    "r": (255, 82, 82),
    "y": (250, 190, 45),
    "g": (55, 166, 99),
    "b": (66, 139, 214),
}

DARK_COLORS = {
    "p": (226, 62, 139),
    "t": (22, 157, 157),
    "o": (239, 126, 36),
    "u": (111, 75, 190),
}

CLASSIC_BASE_COLORS = {
    "r": (255, 85, 85),
    "y": (255, 170, 0),
    "g": (0, 170, 0),
    "b": (85, 85, 255),
}

COLOR_NAMES = {
    "r": "R",
    "y": "Y",
    "g": "G",
    "b": "B",
    "p": "P",
    "t": "T",
    "o": "O",
    "u": "V",
}

LIGHT_ACTIONS = ("draw_one", "reverse", "skip", "flip")
DARK_ACTIONS = ("draw_five", "reverse", "skip_everyone", "flip")


def font(size):
    candidates = (
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


FONTS = {size: font(size) for size in (22, 30, 42, 48, 56, 64, 78, 96, 150)}


def centered_text(draw, xy, text, size, fill, stroke=0, stroke_fill=None,
                  spacing=0):
    selected_font = FONTS[size]
    box = draw.multiline_textbbox(
        (0, 0), text, font=selected_font, spacing=spacing,
        stroke_width=stroke,
    )
    width = box[2] - box[0]
    height = box[3] - box[1]
    draw.multiline_text(
        (xy[0] - width / 2, xy[1] - height / 2),
        text,
        font=selected_font,
        fill=fill,
        spacing=spacing,
        align="center",
        stroke_width=stroke,
        stroke_fill=stroke_fill,
    )


def card_base(color):
    """Use the original card's frame, field and white oval verbatim."""
    import resvg_py

    ns = "{http://www.w3.org/2000/svg}"
    root = ET.parse(CLASSIC_DIR / "svg" / "r_1.svg").getroot()
    group = next(node for node in root.iter(ns + "g")
                 if len(node.findall(ns + "path")) == 4)
    # First path is the original oval; remaining paths are the three digits.
    for digit in group.findall(ns + "path")[1:]:
        group.remove(digit)
    field = group.findall(ns + "rect")[1]
    field.set("style", "fill:#{:02x}{:02x}{:02x};stroke:none".format(*color))
    root.set("width", str(SIZE[0]))
    root.set("height", str(SIZE[1]))
    return Image.open(io.BytesIO(resvg_py.svg_to_bytes(
        svg_string=ET.tostring(root, encoding="unicode")))).convert("RGBA")


def corner_labels(draw, label, color_code):
    corner_font = FONTS[48 if len(label) <= 2 else 30]
    draw.text((42, 41), label, font=corner_font, fill="white",
              stroke_width=1, stroke_fill=(0, 0, 0, 80))
    right = COLOR_NAMES[color_code]
    right_box = draw.textbbox((0, 0), right, font=FONTS[42])
    draw.text((291 - (right_box[2] - right_box[0]), 43), right,
              font=FONTS[42], fill="white")

    rotated = Image.new("RGBA", (100, 80), (0, 0, 0, 0))
    rotated_draw = ImageDraw.Draw(rotated)
    rotated_draw.text((5, 2), label, font=corner_font, fill="white")
    rotated = rotated.rotate(180)
    return rotated


def draw_number(color_code, color, value):
    image = card_base(color)
    draw = ImageDraw.Draw(image)
    corner = corner_labels(draw, value, color_code)
    image.alpha_composite(corner, (30, 404))
    centered_text(draw, (170, 257), value, 150, color,
                  stroke=2, stroke_fill=(255, 255, 255))
    return image


def draw_reverse(draw, color):
    draw.arc((92, 177, 248, 333), 205, 35, fill=color, width=22)
    draw.arc((92, 177, 248, 333), 25, 215, fill=color, width=22)
    draw.polygon(((91, 205), (126, 183), (128, 225)), fill=color)
    draw.polygon(((249, 305), (214, 327), (212, 285)), fill=color)


def draw_skip(draw, color, everyone=False):
    if everyone:
        centered_text(draw, (170, 222), "ALL", 56, color)
        center_y = 293
        radius = 50
    else:
        center_y = 257
        radius = 67
    draw.ellipse((170-radius, center_y-radius, 170+radius, center_y+radius),
                 outline=color, width=19)
    draw.line((125, center_y+45, 215, center_y-45), fill=color, width=19)


def draw_flip(draw, color):
    draw.arc((88, 172, 252, 317), 190, 350, fill=color, width=18)
    draw.arc((88, 202, 252, 347), 10, 170, fill=color, width=18)
    draw.polygon(((244, 198), (215, 176), (218, 214)), fill=color)
    draw.polygon(((96, 321), (125, 343), (122, 305)), fill=color)
    centered_text(draw, (170, 260), "FLIP", 42, color)


def draw_stack(draw, color, amount):
    for offset in (18, 9, 0):
        draw.rounded_rectangle((106+offset, 190-offset, 220+offset, 306-offset),
                               radius=12, fill="white", outline=color, width=6)
    centered_text(draw, (167, 253), f"+{amount}", 64, color)


def draw_penalty_original(color_code, amount, wild=False):
    """Reuse the original SVG background and digit outlines for +1/+5."""
    import resvg_py

    ns = "{http://www.w3.org/2000/svg}"
    root = ET.parse(CLASSIC_DIR / "svg" / f"r_{amount}.svg").getroot()
    group = next(node for node in root.iter(ns + "g")
                 if len(node.findall(ns + "path")) == 4)
    paths = group.findall(ns + "path")
    digit = copy.deepcopy(paths[1])
    for node in paths[1:]:
        group.remove(node)
    if wild:
        root = ET.parse(CLASSIC_DIR / "svg" / "colorchooser.svg").getroot()
        wild_group = next(node for node in root.iter(ns + "g")
                          if len(node.findall(ns + "rect")) == 2)
        palette_paths = wild_group.findall(ns + "path")
        # Replace the small corner palettes with +2, as on the +1/+5 cards.
        for node in palette_paths[5:13] + palette_paths[14:]:
            wild_group.remove(node)
    # Digit coordinates in the existing Inkscape source artwork.
    origin_x = {1: 83, 2: 139, 5: 321}[amount]
    digit_width = 10 if amount == 1 else 20
    width = 14 + digit_width
    def symbol(x, y, scale, fill, rotate=False):
        transform = f"translate({x} {y})"
        if rotate:
            transform += " rotate(180)"
        outer = ET.SubElement(root, ns + "g", {
            "transform": transform + f" scale({scale})", "fill": fill})
        ET.SubElement(outer, ns + "path", {
            "d": "M0 12 H4 V8 H8 V12 H12 V16 H8 V20 H4 V16 H0 Z"})
        number = copy.deepcopy(digit)
        number.attrib.pop("id", None)
        number.set("style", f"fill:{fill};stroke:none")
        number.set("transform", f"translate({14-origin_x} -362.36217)")
        outer.append(number)
    symbol(121-width*3.5/2, 128, 3.5, "#ffffff" if wild else "#ff5555")
    symbol(30, 30, 1.45, "#ffffff")
    symbol(212, 332, 1.45, "#ffffff", rotate=True)
    root.set("width", "340")
    root.set("height", "512")
    image = Image.open(io.BytesIO(resvg_py.svg_to_bytes(
        svg_string=ET.tostring(root, encoding="unicode")))).convert("RGBA")
    if wild:
        return image
    if color_code in DARK_COLORS:
        image = recolor(image, CLASSIC_BASE_COLORS['r'], DARK_COLORS[color_code])
        return add_dark_marker(image, COLOR_NAMES[color_code])
    # Use the exact source color of the corresponding original number card.
    reference = Image.open(CLASSIC_DIR / "png" / f"{color_code}_1.png")
    target = reference.convert("RGB").getpixel((170, 60))
    image = recolor(image, CLASSIC_BASE_COLORS['r'], target)
    image.alpha_composite(Image.open(OVERLAY_DIR / f"{color_code}.png").convert("RGBA"))
    return image


def draw_skip_all_original(color_code):
    """Place the supplied reset symbol like the classic Skip, without text."""
    import resvg_py

    color = (DARK_COLORS[color_code] if color_code in DARK_COLORS else
             Image.open(CLASSIC_DIR / "png" / f"{color_code}_1.png")
             .convert("RGB").getpixel((170, 60)))
    image = card_base(color)
    ns = "{http://www.w3.org/2000/svg}"
    source = ET.parse(IMAGES_DIR.parent / "reset-svgrepo-com.svg").getroot()
    def symbol(size, fill):
        root = copy.deepcopy(source)
        root.set("fill", fill)
        root.set("width", str(size))
        root.set("height", str(size))
        return Image.open(io.BytesIO(resvg_py.svg_to_bytes(
            svg_string=ET.tostring(root, encoding="unicode")))).convert("RGBA")
    image.alpha_composite(symbol(168, "#{:02x}{:02x}{:02x}".format(*color)),
                          (86, 172))
    corner = symbol(70, "#ffffff")
    image.alpha_composite(corner, (42, 43))
    image.alpha_composite(corner.transpose(Image.Transpose.ROTATE_180),
                          (228, 399))
    return image


def draw_flip_original(color_code):
    """Wrap the supplied playing card with an arrow passing behind/in front."""
    import resvg_py

    color = (DARK_COLORS[color_code] if color_code in DARK_COLORS else
             Image.open(CLASSIC_DIR / "png" / f"{color_code}_1.png")
             .convert("RGB").getpixel((170, 60)))
    image = card_base(color)
    color_hex = "#{:02x}{:02x}{:02x}".format(*color)
    ns = "{http://www.w3.org/2000/svg}"
    source = ET.parse(IMAGES_DIR.parent / "playing-card.svg").getroot()

    def symbol(size, foreground, background):
        root = ET.Element(ns + "svg", {
            "viewBox": "0 0 48 40", "width": str(size),
            "height": str(round(size * 40 / 48)), "color": foreground})
        # Far half of the ring, occluded by the card in the middle.
        ET.SubElement(root, ns + "path", {
            "d": "M3 20 C3 8 45 8 45 20", "fill": "none",
            "stroke": foreground, "stroke-width": "2.6"})
        card = ET.SubElement(root, ns + "g", {
            "transform": "translate(24 20) scale(1.75) translate(-12 -12)"})
        ET.SubElement(card, ns + "rect", {
            "x": "5", "y": "2", "width": "14", "height": "20",
            "rx": "2", "fill": background})
        for element in source:
            if element.tag != ns + "title":
                card.append(copy.deepcopy(element))
        # Near half crosses the card; the background stroke separates lines.
        near = "M3 20 C3 32 45 32 45 20"
        for stroke, width in ((background, "5.2"), (foreground, "2.6")):
            ET.SubElement(root, ns + "path", {
                "d": near, "fill": "none", "stroke": stroke,
                "stroke-width": width})
        ET.SubElement(root, ns + "path", {
            "d": "M40 23 L45 16 L48 24 Z", "fill": foreground})
        return Image.open(io.BytesIO(resvg_py.svg_to_bytes(
            svg_string=ET.tostring(root, encoding="unicode")))).convert("RGBA")

    image.alpha_composite(symbol(200, color_hex, "#ffffff"), (70, 173))
    corner = symbol(80, "#ffffff", color_hex)
    image.alpha_composite(corner, (36, 43))
    image.alpha_composite(corner.transpose(Image.Transpose.ROTATE_180),
                          (224, 402))
    return image


def draw_action(color_code, color, action):
    if action == "flip":
        return draw_flip_original(color_code)
    if action == "skip_everyone":
        return draw_skip_all_original(color_code)
    if action in ("draw_one", "draw_five"):
        return draw_penalty_original(color_code, 1 if action == "draw_one" else 5)
    image = card_base(color)
    draw = ImageDraw.Draw(image)
    labels = {
        "draw_one": "+1",
        "draw_five": "+5",
        "reverse": "REV",
        "skip": "Ø",
        "skip_everyone": "ALL",
        "flip": "F",
    }
    label = labels[action]
    corner = corner_labels(draw, label, color_code)
    image.alpha_composite(corner, (30, 404))

    if action == "reverse":
        draw_reverse(draw, color)
    elif action == "skip":
        draw_skip(draw, color)
    elif action == "skip_everyone":
        draw_skip(draw, color, everyone=True)
    elif action == "flip":
        draw_flip(draw, color)
    elif action == "draw_one":
        draw_stack(draw, color, 1)
    elif action == "draw_five":
        draw_stack(draw, color, 5)
    return image


def draw_dark_wild(draw_color=False):
    """Original wild palette, with an optional two-layer draw symbol."""
    import resvg_py

    ns = "{http://www.w3.org/2000/svg}"
    root = ET.parse(CLASSIC_DIR / "svg" / "colorchooser.svg").getroot()
    # Both dark Wild cards retain the original white outer frame.
    frame = next(root.iter(ns + 'rect'))
    replacements = {
        "fill:#000000": "fill:#E2DFE5",
        "fill:#ff5555": "fill:#{:02x}{:02x}{:02x}".format(*DARK_COLORS['p']),
        "fill:#ffaa00": "fill:#{:02x}{:02x}{:02x}".format(*DARK_COLORS['o']),
        "fill:#00aa00": "fill:#{:02x}{:02x}{:02x}".format(*DARK_COLORS['t']),
        "fill:#5555ff": "fill:#{:02x}{:02x}{:02x}".format(*DARK_COLORS['u']),
    }
    for node in root.iter():
        style = node.get('style', '')
        for source, target in replacements.items():
            if node is frame and source == 'fill:#000000':
                continue
            style = style.replace(source, target)
        if style:
            node.set('style', style)

    if draw_color:
        source = ET.parse(IMAGES_DIR.parent / "stack-pop.svg").getroot()
        source_paths = source.findall('.//' + ns + 'path')
        # Layer 1: rounded, elongated cards derived from the stack silhouette.
        stack = ET.SubElement(root, ns + 'g', {
            'id': 'draw-stack', 'transform': 'translate(71 124) scale(6.25)',
            'stroke': '#ffffff', 'stroke-width': '1.25',
            'stroke-linejoin': 'round', 'stroke-linecap': 'round'})
        ET.SubElement(stack, ns + 'path', {
            'd': 'M2 10.2 Q1.4 10.5 2 11 L7.5 15.5 Q8 15.9 8.5 15.5 '
                 'L14 11 Q14.6 10.5 14 10.2 L8.5 6 Q8 5.6 7.5 6 Z',
            'fill': '#E2DFE5'})
        ET.SubElement(stack, ns + 'path', {
            'd': 'M2 7.2 Q1.4 7.5 2 8 L7.5 12.5 Q8 12.9 8.5 12.5 '
                 'L14 8 Q14.6 7.5 14 7.2 L8.5 3 Q8 2.6 7.5 3 Z',
            'fill': '#E2DFE5'})
        # Layer 2: the upward arrow from the supplied stack-pop SVG.
        arrow = ET.SubElement(root, ns + 'g', {
            'id': 'draw-arrow', 'transform': 'translate(71 110) scale(6.25)',
            'fill': 'none', 'stroke': '#45414B', 'stroke-width': '1.5',
            'stroke-linecap': 'round', 'stroke-linejoin': 'round'})
        arrow.append(copy.deepcopy(source_paths[1]))
    root.set('width', '340')
    root.set('height', '512')
    return Image.open(io.BytesIO(resvg_py.svg_to_bytes(
        svg_string=ET.tostring(root, encoding='unicode')))).convert('RGBA')


def draw_wild(side, action):
    if side == 'dark':
        return draw_dark_wild(draw_color=action == 'draw_color')
    if action == 'wild_draw_two':
        return draw_penalty_original(None, 2, wild=True)
    colors = LIGHT_COLORS if side == "light" else DARK_COLORS
    image = card_base((30, 31, 39))
    draw = ImageDraw.Draw(image)
    palette = list(colors.values())
    circle = (88, 176, 252, 340)
    for index, start in enumerate((0, 90, 180, 270)):
        draw.pieslice(circle, start=start, end=start+90,
                      fill=palette[index], outline="white", width=3)
    draw.ellipse(circle, outline=(30, 31, 39), width=8)

    labels = {
        "colorchooser": "WILD",
        "wild_draw_two": "+2",
        "draw_color": "DRAW\nCOLOR",
    }
    label = labels[action]
    text_size = 56 if action != "draw_color" else 30
    centered_text(draw, (170, 258), label, text_size, "white",
                  stroke=4, stroke_fill=(30, 31, 39), spacing=-4)
    corner_label = {
        "colorchooser": "W",
        "wild_draw_two": "+2",
        "draw_color": "DC",
    }[action]
    draw.text((46, 48), corner_label, font=FONTS[30], fill="white")
    return image


def custom_unavailable(image):
    image = ImageEnhance.Color(image).enhance(0.16)
    image = ImageEnhance.Brightness(image).enhance(0.72)
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((29, 30, 311, 482), radius=30,
                           fill=(20, 20, 24, 55))
    draw.line((76, 411, 264, 101), fill=(255, 255, 255, 210), width=23)
    draw.line((76, 411, 264, 101), fill=(75, 75, 80, 255), width=11)
    image.alpha_composite(overlay)
    return image


def asset_paths(side, key):
    side_dir = OUTPUT_DIR / side
    return {
        "png": side_dir / "png" / f"{key}.png",
        "webp": side_dir / "webp" / f"{key}.webp",
        "png_not_playable": side_dir / "png_not_playable" / f"{key}.png",
        "webp_not_playable": side_dir / "webp_not_playable" / f"{key}.webp",
    }


def register(manifest, side, key, paths):
    manifest["normal"][side][key] = paths["webp"].relative_to(
        IMAGES_DIR).as_posix()
    manifest["not_playable"][side][key] = paths[
        "webp_not_playable"].relative_to(IMAGES_DIR).as_posix()


def save_custom_card(side, key, image, manifest, overwrite=False):
    """Create a new action card only when explicitly requested or missing."""
    paths = asset_paths(side, key)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    if overwrite or not all(path.exists() for path in paths.values()):
        if paths["png"].exists() and not overwrite:
            image = Image.open(paths["png"]).convert("RGBA")
        disabled = (standard_unavailable(image.copy())
                    if key.endswith(("draw_one", "draw_five", "skip_everyone", "_flip")) or
                    key == 'wild_draw_two' or
                    (side == 'dark' and key in ('colorchooser', 'draw_color'))
                    else custom_unavailable(image.copy()))
        if paths["png_not_playable"].exists() and not overwrite:
            disabled = Image.open(paths["png_not_playable"]).convert("RGBA")
        for kind, path in paths.items():
            if path.exists() and not overwrite:
                continue
            selected = disabled if "not_playable" in kind else image
            if path.suffix == ".webp":
                selected.save(path, "WEBP", lossless=True, method=6)
            else:
                selected.save(path, optimize=True)
    register(manifest, side, key, paths)


def copy_original_light(key, source_key, manifest):
    """Copy the bot's existing card bytes without rendering them again."""
    paths = asset_paths("light", key)
    sources = {
        "png": CLASSIC_COLORBLIND_DIR / "png" / f"{source_key}.png",
        "webp": CLASSIC_COLORBLIND_DIR / "webp" / f"{source_key}.webp",
        "png_not_playable": CLASSIC_COLORBLIND_DIR /
        "png_not_playable" / f"{source_key}.png",
        "webp_not_playable": CLASSIC_COLORBLIND_DIR /
        "webp_not_playable" / f"{source_key}.webp",
    }
    for kind, destination in paths.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        copyfile(sources[kind], destination)
    register(manifest, "light", key, paths)


def recolor(image, source_color=None, target_color=None, wild_palette=False):
    """Replace only saturated source colors, preserving geometry and shading."""
    rgba = image.convert("RGBA")
    pixels = []
    wild_targets = {
        "r": DARK_COLORS["p"],
        "y": DARK_COLORS["o"],
        "g": DARK_COLORS["t"],
        "b": DARK_COLORS["u"],
    }

    def transform(hue, saturation, value, source, target):
        _, source_saturation, source_value = colorsys.rgb_to_hsv(
            *(channel / 255 for channel in source))
        target_hue, target_saturation, target_value = colorsys.rgb_to_hsv(
            *(channel / 255 for channel in target))
        saturation = min(1, saturation * target_saturation /
                         source_saturation)
        value = min(1, value * target_value / source_value)
        return target_hue, saturation, value

    for red, green, blue, alpha in rgba.get_flattened_data():
        hue, saturation, value = colorsys.rgb_to_hsv(
            red / 255, green / 255, blue / 255)
        if alpha and saturation > 0.22 and value > 0.18:
            if wild_palette:
                degrees = hue * 360
                if degrees < 25 or degrees >= 330:
                    source_key = "r"
                elif degrees < 85:
                    source_key = "y"
                elif degrees < 175:
                    source_key = "g"
                else:
                    source_key = "b"
                hue, saturation, value = transform(
                    hue, saturation, value,
                    CLASSIC_BASE_COLORS[source_key],
                    wild_targets[source_key],
                )
            else:
                hue, saturation, value = transform(
                    hue, saturation, value, source_color, target_color)
            red, green, blue = (
                round(channel * 255)
                for channel in colorsys.hsv_to_rgb(hue, saturation, value)
            )
        pixels.append((red, green, blue, alpha))
    rgba.putdata(pixels)
    return rgba


def add_dark_marker(image, marker):
    """Apply the same corner-marker convention as the classic colorblind deck."""
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    marker_font = font(64)
    draw.text((247, 38), marker, font=marker_font, fill="white")
    rotated = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
    ImageDraw.Draw(rotated).text((7, 5), marker, font=marker_font, fill="white")
    overlay.alpha_composite(rotated.rotate(180), (26, 400))
    image.alpha_composite(overlay)
    return image


def standard_unavailable(image):
    """Use the classic deck's subdued treatment and original red frame."""
    image = ImageEnhance.Color(image).enhance(0.20)
    image = ImageEnhance.Brightness(image).enhance(0.75)
    image = ImageEnhance.Contrast(image).enhance(1.10)
    frame = Image.open(OVERLAY_DIR / "not_playable.png").convert("RGBA")
    image.alpha_composite(frame)
    return image


def save_dark_original(key, source_key, marker, manifest,
                       wild_palette=False):
    paths = asset_paths("dark", key)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    source = Image.open(CLASSIC_DIR / "png" / f"{source_key}.png")
    marker_targets = {"P": DARK_COLORS["p"], "T": DARK_COLORS["t"],
                      "O": DARK_COLORS["o"], "V": DARK_COLORS["u"]}
    source_color = CLASSIC_BASE_COLORS.get(source_key.split("_", 1)[0])
    normal = recolor(source, source_color, marker_targets.get(marker),
                     wild_palette)
    if key == 'colorchooser':
        normal = draw_dark_wild()
    if marker:
        normal = add_dark_marker(normal, marker)
    disabled = standard_unavailable(normal.copy())

    normal.save(paths["png"], optimize=True)
    normal.save(paths["webp"], "WEBP", lossless=True, method=6)
    disabled.save(paths["png_not_playable"], optimize=True)
    disabled.save(paths["webp_not_playable"], "WEBP", lossless=True,
                  method=6)
    register(manifest, "dark", key, paths)


def generate_reused_cards(manifest):
    for color_code in LIGHT_COLORS:
        for number in range(1, 10):
            key = f"{color_code}_{number}"
            copy_original_light(key, key, manifest)
        for action in ("reverse", "skip"):
            key = f"{color_code}_{action}"
            copy_original_light(key, key, manifest)
    copy_original_light("colorchooser", "colorchooser", manifest)

    dark_sources = {
        "p": ("r", "P"),
        "t": ("b", "T"),
        "o": ("y", "O"),
        "u": ("b", "V"),
    }
    for color_code, (source_color, marker) in dark_sources.items():
        for number in range(1, 10):
            save_dark_original(
                f"{color_code}_{number}", f"{source_color}_{number}",
                marker, manifest,
            )
        save_dark_original(
            f"{color_code}_reverse", f"{source_color}_reverse",
            marker, manifest,
        )
    save_dark_original("colorchooser", "colorchooser", None, manifest,
                       wild_palette=True)


def generate_new_specials(manifest, overwrite=False):
    for color_code, color in LIGHT_COLORS.items():
        for action in ("draw_one", "flip"):
            key = f"{color_code}_{action}"
            save_custom_card("light", key,
                             draw_action(color_code, color, action), manifest,
                             overwrite)
    save_custom_card("light", "wild_draw_two",
                     draw_wild("light", "wild_draw_two"), manifest, overwrite)

    for color_code, color in DARK_COLORS.items():
        for action in ("draw_five", "skip_everyone", "flip"):
            key = f"{color_code}_{action}"
            save_custom_card("dark", key,
                             draw_action(color_code, color, action), manifest,
                             overwrite)
    save_custom_card("dark", "draw_color",
                     draw_wild("dark", "draw_color"), manifest, overwrite)


def order_manifest(manifest):
    light_order = [
        f"{color}_{value}"
        for color in LIGHT_COLORS
        for value in tuple(str(number) for number in range(1, 10)) +
        ("draw_one", "reverse", "skip", "flip")
    ] + ["colorchooser", "wild_draw_two"]
    dark_order = [
        f"{color}_{value}"
        for color in DARK_COLORS
        for value in tuple(str(number) for number in range(1, 10)) +
        ("draw_five", "reverse", "skip_everyone", "flip")
    ] + ["colorchooser", "draw_color"]
    for group in ("normal", "not_playable"):
        manifest[group]["light"] = {
            key: manifest[group]["light"][key] for key in light_order}
        manifest[group]["dark"] = {
            key: manifest[group]["dark"][key] for key in dark_order}


def create_preview(side, keys):
    columns = 9
    cell_size = (112, 168)
    rows = (len(keys) + columns - 1) // columns
    preview = Image.new("RGBA", (columns * cell_size[0],
                                  rows * cell_size[1]), (28, 29, 36, 255))
    for index, key in enumerate(keys):
        card = Image.open(OUTPUT_DIR / side / "png" / f"{key}.png")
        card.thumbnail((100, 152), Image.Resampling.LANCZOS)
        x = (index % columns) * cell_size[0] + (cell_size[0]-card.width)//2
        y = (index // columns) * cell_size[1] + (cell_size[1]-card.height)//2
        preview.alpha_composite(card, (x, y))
    preview.convert("RGB").save(OUTPUT_DIR / f"preview_{side}.jpg",
                                quality=92, optimize=True)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite-new-specials", action="store_true",
        help="also recreate the new action cards intended for manual editing",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = {
        "normal": {"light": {}, "dark": {}},
        "not_playable": {"light": {}, "dark": {}},
    }
    generate_reused_cards(manifest)
    generate_new_specials(manifest, args.overwrite_new_specials)
    order_manifest(manifest)
    create_preview("light", manifest["normal"]["light"].keys())
    create_preview("dark", manifest["normal"]["dark"].keys())

    manifest_path = OUTPUT_DIR / "asset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n",
                             encoding="utf-8")
    generated = sum(len(cards) for group in manifest.values()
                    for cards in group.values())
    print(f"Generated {generated} WebP stickers and matching PNG previews")


if __name__ == "__main__":
    main()
