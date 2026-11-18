"""Paint each theme's and faction's texture atlas, glow map, surface map, and card map.

Run from the game project, with Pillow available:

    uv run --with pillow python "$SKILL_DIR/scripts/atlas_painter.py"
    python3 "$SKILL_DIR/scripts/atlas_painter.py"      # if Pillow is already installed

The project's cards live in <materials>/atlas_sets.py, where <materials> is
paths.materials in rts-art.json. That file defines:

    CARDS     name: ((width, height) in pixels, base color, what it shows)
    BASE      cards every theme's atlas carries (a faction's atlas never does)
    THEMES    name: {"lighting": preset, "glow": bool, "cards": [...]}
    FACTIONS  name: {"lighting": preset, "glow": bool, "surface": bool, "cards": [...]}
    paint(card)  paints one card, using the helpers in this module

Optional settings in a set: "fill_gaps": True packs late cards into gaps on
full pages, and "clean": True skips the base noise and the closing stipple,
for spotless sets. A card's default finish comes from DEFAULT_FINISH in
atlas_sets.py, (roughness, metallic), and paint() may paint over it.

Each set gets <materials>/<themes|factions>/<name>/atlas.jpg and atlas.json,
plus atlas-glow.jpg when it glows and atlas-surface.jpg, a roughness (green)
and metallic (blue) map, when it has a surface. Cards pack in list order onto
2048-pixel pages laid side by side.

Cards may move when lists change. Structures mapped with atlas_cards.py record
which card each face uses, so atlas_cards.refresh() fits them again.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as projects  # noqa: E402

PAGE = 2048
PAD = 12
MATTE = (.86, 0)
resample = Image.Resampling.BICUBIC
# Fonts tried in order when rts-art.json names none: macOS, Windows, then common Linux paths.
FONT_SEARCH = {
    "regular": [
        "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "condensed": [
        "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
        "C:/Windows/Fonts/ARIALNB.TTF",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    ],
}


class Card:
    """One card being painted: its color image, glow map, and surface map, each with a drawing."""

    def __init__(self, name, size, base, finish_default, clean):
        self.name, self.size, self.base = name, size, base
        self.w, self.h = size
        # Each card seeds its own noise, so adding a card never repaints the others.
        self.rng = random.Random(name)
        self.clean = clean
        self.im = Image.new("RGB", size, base) if clean else field(self, base)
        self.d = ImageDraw.Draw(self.im)
        # Glow is black where nothing glows.
        self.glow = Image.new("RGB", size, (0, 0, 0))
        self.gd = ImageDraw.Draw(self.glow)
        self.surface = Image.new("RGB", size, finish(finish_default))
        self.rd = ImageDraw.Draw(self.surface)


_fonts = {}


def font(kind, size):
    configured = _fonts.get(kind)
    for path in ([configured] if configured else []) + FONT_SEARCH[kind]:
        if Path(path).is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def text(d, at, label, size, color, condensed=False):
    """Centered text, for signs. Fonts come from rts-art.json, or the first system font found."""
    d.text(at, label, font=font("condensed" if condensed else "regular", size), fill=color, anchor="mm")


def field(card, base, coarse=8, grain=4, edge=12):
    """A noisy base color with darker edges. Pass a larger `coarse` for broad surfaces like roofs and lots."""
    w, h = card.size
    rng = card.rng

    def noise(step):
        small = Image.new("L", (max(2, w // step), max(2, h // step)))
        small.putdata([rng.randrange(256) for _ in range(small.width * small.height)])
        return list(small.resize(card.size, resample).tobytes())

    broad, mid = noise(73), noise(16)
    im = Image.new("RGB", card.size)
    pixels = []
    for i, (n1, n2) in enumerate(zip(broad, mid)):
        x, y = i % w, i // w
        ao = edge * math.exp(-min(x, w - x - 1, y, h - y - 1) / 9)
        offset = (n1 - 128) * coarse / 128 + (n2 - 128) * .052 + rng.randint(-grain, grain) - ao
        pixels.append(tuple(max(0, min(255, round(v + offset))) for v in base))
    im.putdata(pixels)
    return im


def rebase(card, coarse):
    """Repaint the card's base noise, for broad surfaces that want more variation."""
    card.im.paste(field(card, card.base, coarse))


def grime(card, contacts=(), streaks=0):
    """Dirt: soft dark boxes at contact areas (x0, y0, x1, y1, strength) and streaks running down."""
    w, h = card.size
    rng = card.rng
    mask = Image.new("L", card.size)
    d = ImageDraw.Draw(mask)
    for x0, y0, x1, y1, power in contacts:
        d.rectangle((x0, y0, x1, y1), fill=power)
    for _ in range(streaks):
        x = rng.randrange(w)
        y = rng.choice([rng.randrange(max(1, h // 3)), rng.randrange(h)])
        reach = rng.randrange(5, max(6, h // 3))
        d.line((x, y, x + rng.randrange(-2, 3), y + reach), fill=rng.randint(18, 53), width=rng.randint(1, 4))
    card.im.paste((36, 38, 35), (0, 0), mask.filter(ImageFilter.GaussianBlur(4.5)))


def glass(d, x0, y0, x1, y1, divisions, door=False):
    """A tinted window with a frame, mullions, a reflection, and a sill. `door` adds handles."""
    d.rectangle((x0, y0, x1, y1 + 4), fill=(85, 86, 81))
    d.rectangle((x0 + 3, y0 + 2, x1 - 3, y1 - 2), fill=(54, 63, 66))
    d.rectangle((x0 + 5, y0 + 5, x1 - 5, y1 - 4), fill=(83, 104, 116))
    dy = y1 - y0
    d.polygon([(x0 + 5, y0 + int(dy * .70)), (x1 - 5, y0 + int(dy * .32)), (x1 - 5, y1 - 4), (x0 + 5, y1 - 4)],
              fill=(61, 79, 89))
    if dy > 45:
        d.line((x0 + 5, y0 + int(dy * .23), x1 - 5, y0 + int(dy * .23)), fill=(115, 127, 130), width=2)
    for i in range(1, divisions):
        x = x0 + round((x1 - x0) * i / divisions)
        d.rectangle((x - 2, y0 + 3, x + 2, y1 - 2), fill=(58, 69, 73))
        d.line((x - 1, y0 + 4, x - 1, y1 - 3), fill=(119, 129, 128), width=1)
    d.line((x0, y1 + 3, x1, y1 + 3), fill=(172, 171, 157), width=2)
    if door:
        x = (x0 + x1) // 2
        for xx in (x - 7, x + 6):
            d.rounded_rectangle((xx, y0 + dy // 2, xx + 2, y0 + dy // 2 + 13), radius=1, fill=(166, 173, 166))


def seams(d, w, h, spacing, rows, dark=(120, 116, 107), light=(165, 160, 146)):
    """Vertical panel seams every `spacing` pixels and horizontal floor lines at `rows`."""
    for x in range(3, w, spacing):
        d.line((x, 1, x, h - 1), fill=dark)
        d.line((x + 1, 1, x + 1, h - 1), fill=light)
    for y in rows:
        d.line((0, y, w, y), fill=dark, width=2)
        d.line((0, y + 2, w, y + 2), fill=light, width=1)


def joints(d, w, h, spacing, color, light, rows=()):
    """Fine panel joints, a dark line with a light edge beside it."""
    for x in range(spacing, w, spacing):
        d.line((x, 0, x, h), fill=color)
        d.line((x + 1, 0, x + 1, h), fill=light)
    for y in rows:
        d.line((0, y, w, y), fill=color)
        d.line((0, y + 1, w, y + 1), fill=light)


def finish(rough_metal):
    """A surface-map color: green is roughness and blue is metallic."""
    rough, metal = rough_metal
    return (255, round(rough * 255), round(metal * 255))


def lerp(start, end, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(start, end))


def wash(glow, box, color, blur, strength=255):
    """A soft glow that fades out from `box`, never a hard edge."""
    mask = Image.new("L", glow.size)
    ImageDraw.Draw(mask).rectangle(box, fill=strength)
    glow.paste(color, (0, 0), mask.filter(ImageFilter.GaussianBlur(blur)))


def rust(card, count, top=0, color=(104, 68, 42)):
    """Rust streaks running down from rows near `top`."""
    w, h = card.size
    rng = card.rng
    mask = Image.new("L", card.size)
    d = ImageDraw.Draw(mask)
    for _ in range(count):
        x = rng.randrange(w)
        y = top + rng.randrange(max(1, h // 4))
        d.line((x, y, x + rng.randrange(-2, 3), y + rng.randrange(8, max(9, h // 2))),
               fill=rng.randint(80, 170), width=rng.randint(1, 4))
    card.im.paste(color, (0, 0), mask.filter(ImageFilter.GaussianBlur(1.5)))


def stains(card, count, color=(26, 28, 31)):
    """Soft dark stains scattered over the card."""
    rng = card.rng
    mask = Image.new("L", card.size)
    d = ImageDraw.Draw(mask)
    for _ in range(count):
        x, y = rng.randrange(card.w), rng.randrange(card.h)
        d.ellipse((x - rng.randrange(8, 30), y - rng.randrange(6, 20), x + rng.randrange(8, 30), y + rng.randrange(6, 20)),
                  fill=rng.randint(60, 140))
    card.im.paste(color, (0, 0), mask.filter(ImageFilter.GaussianBlur(5)))


def shutter(d, x0, y0, x1, y1, up=0):
    """A roller shutter, raised by `up` pixels."""
    d.rectangle((x0, y0, x1, y1), fill=(30, 33, 37))
    for y in range(y0 + up, y1, 5):
        d.line((x0, y, x1, y), fill=(78, 82, 86))
        d.line((x0, y + 1, x1, y + 1), fill=(58, 62, 66))


def hazard(card, x0, y0, x1, y1, step=10, color=(140, 122, 58)):
    """Diagonal warning stripes filling a box, `color` and near-black."""
    w, h = x1 - x0 + 1, y1 - y0 + 1
    band = Image.new("RGB", (w, h), color)
    bd = ImageDraw.Draw(band)
    for x in range(-h, w + h, step):
        bd.polygon([(x, h), (x + step // 2, h), (x + step // 2 + h, 0), (x + h, 0)], fill=(26, 26, 24))
    card.im.paste(band, (x0, y0))


def stipple(card):
    """Break up perfectly even paint without eroding small lettering at game zoom."""
    rng = card.rng
    mask = Image.new("L", card.size)
    d = ImageDraw.Draw(mask)
    for _ in range(card.w * card.h // 235):
        x, y = rng.randrange(card.w), rng.randrange(card.h)
        d.line((x, y, x + rng.choice([0, 1, 2]), y), fill=rng.randrange(12, 53))
    card.im.paste((55, 55, 49), (0, 0), mask)


def paste(atlas, im, x, y):
    """Paste a card and bleed its edges into the padding so mipmaps don't pick up neighbors."""
    w, h = im.size
    atlas.paste(im, (x, y))
    atlas.paste(im.crop((0, 0, 1, h)).resize((PAD, h)), (x - PAD, y))
    atlas.paste(im.crop((w - 1, 0, w, h)).resize((PAD, h)), (x + w, y))
    strip = atlas.crop((x - PAD, y, x + w + PAD, y + 1)).resize((w + 2 * PAD, PAD))
    atlas.paste(strip, (x - PAD, y - PAD))
    strip = atlas.crop((x - PAD, y + h - 1, x + w + PAD, y + h)).resize((w + 2 * PAD, PAD))
    atlas.paste(strip, (x - PAD, y + h))


def page_gap(cards, regions, page, width, height):
    """Find space for a padded card without moving cards already on this page."""
    offset = page * PAGE
    rects = []
    for name, (x, y) in regions.items():
        if offset <= x < offset + PAGE:
            w, h = cards[name][0]
            rects.append((x - offset - PAD, y - PAD, x - offset + w + PAD, y + h + PAD))
    xs = sorted({0, *(right for _, _, right, _ in rects)})
    ys = sorted({0, *(bottom for _, _, _, bottom in rects)})
    for y in ys:
        bottom = y + height + 2 * PAD
        for x in xs:
            right = x + width + 2 * PAD
            if right <= PAGE and bottom <= PAGE and all(
                right <= left or x >= r or bottom <= top or y >= b for left, top, r, b in rects
            ):
                return offset + x + PAD, y + PAD
    return None


def pack(cards, names, *, fill_gaps=False):
    """Shelf-pack cards onto 2048-pixel pages, optionally filling gaps when a page overflows."""
    regions, page, x, y, row = {}, 0, PAD, PAD, 0
    filling_gaps = False
    for name in names:
        w, h = cards[name][0]
        if w + 2 * PAD > PAGE or h + 2 * PAD > PAGE:
            raise ValueError(f"Card {name} is larger than a {PAGE}-pixel page")
        if not filling_gaps and x + w + PAD > PAGE:
            x, y, row = PAD, y + row + 2 * PAD, 0
        if filling_gaps or y + h + PAD > PAGE:
            gap = page_gap(cards, regions, page, w, h) if fill_gaps else None
            if gap is not None:
                regions[name] = gap
                filling_gaps = True
                continue
            page, x, y, row = page + 1, PAD, PAD, 0
            filling_gaps = False
        regions[name] = (page * PAGE + x, y)
        x += w + 2 * PAD
        row = max(row, h)
    return regions, page + 1


def load_sets(path):
    if not path.is_file():
        raise SystemExit(f"No card definitions at {path}. Copy the skill's templates/atlas_sets.py there first.")
    # atlas_sets.py imports its helpers from atlas_painter, which must be this running module.
    sys.modules.setdefault("atlas_painter", sys.modules[__name__])
    spec = importlib.util.spec_from_file_location("atlas_sets", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    arguments = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    arguments.add_argument("--root", type=Path, help="The game project, if not the current folder or above it")
    arguments.add_argument("--only", help="Paint only this set, such as themes/industrial or factions/vanguard")
    options = arguments.parse_args()
    project = projects.load(options.root)
    _fonts.update({key: value for key, value in project.fonts.items() if value})
    materials = project.paths["materials"]
    sets_module = load_sets(materials / "atlas_sets.py")
    cards = sets_module.CARDS
    base = getattr(sets_module, "BASE", [])
    default_finish = getattr(sets_module, "DEFAULT_FINISH", MATTE)
    lighting = set(project.lighting_names())

    sets = [("themes", name, base + settings["cards"], settings) for name, settings in sets_module.THEMES.items()]
    sets += [("factions", name, settings["cards"], settings) for name, settings in sets_module.FACTIONS.items()]
    if options.only:
        sets = [entry for entry in sets if f"{entry[0]}/{entry[1]}" == options.only]
        if not sets:
            arguments.error(f"No set {options.only} in atlas_sets.py")
    for kind, name, names, settings in sets:
        if len(set(names)) != len(names):
            raise SystemExit(f"{name} lists a card twice")
        unknown = [card for card in names if card not in cards]
        if unknown:
            raise SystemExit(f"{name} lists cards missing from CARDS: {', '.join(unknown)}")
        if settings["lighting"] not in lighting:
            raise SystemExit(f"{name} uses lighting {settings['lighting']!r}, which rts-art.json does not define")

        painted = {}
        for card_name in names:
            size, color, _ = cards[card_name]
            card = Card(card_name, size, color, default_finish, settings.get("clean", False))
            sets_module.paint(card)
            if not card.clean:
                stipple(card)
            painted[card_name] = (card.im, card.glow, card.surface)

        regions, pages = pack(cards, names, fill_gaps=settings.get("fill_gaps", False))
        folder = materials / kind / name
        folder.mkdir(parents=True, exist_ok=True)
        atlas = Image.new("RGB", (PAGE * pages, PAGE), (86, 91, 89))
        glow = Image.new("RGB", atlas.size, (0, 0, 0))
        surface = Image.new("RGB", atlas.size, finish(default_finish))
        for card_name in names:
            for layer, image in zip((atlas, glow, surface), painted[card_name]):
                paste(layer, image, *regions[card_name])
        atlas.save(folder / "atlas.jpg", quality=88, subsampling=0, optimize=True)
        if settings["glow"]:
            glow.save(folder / "atlas-glow.jpg", quality=90, subsampling=0, optimize=True)
        if settings.get("surface"):
            surface.save(folder / "atlas-surface.jpg", quality=92, subsampling=0, optimize=True)
        document = {
            kind[:-1]: name, "width": atlas.width, "height": atlas.height, "lighting": settings["lighting"],
            "glow": "atlas-glow.jpg" if settings["glow"] else None,
            "surface": "atlas-surface.jpg" if settings.get("surface") else None,
            "cards": {
                card_name: {"x": regions[card_name][0], "y": regions[card_name][1], "width": cards[card_name][0][0],
                            "height": cards[card_name][0][1], "shows": cards[card_name][2]}
                for card_name in names
            },
        }
        (folder / "atlas.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"{folder} ({len(names)} cards on {pages} page{'s' if pages > 1 else ''})")


if __name__ == "__main__":
    main()
