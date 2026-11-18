"""The project's atlas cards and sets, painted by the blender-rts-structures skill's atlas_painter.py.

Run from the project root, with Pillow available:

    uv run --with pillow python "<skill folder>/scripts/atlas_painter.py"

CARDS defines every card once. BASE lists neutral cards that every theme's atlas
carries. THEMES and FACTIONS list each set's own cards and settings, and a
faction's atlas holds only its own cards. Start a faction's card names with its
ID, such as vanguard_shell, since CARDS is shared. List cards tallest first so
they pack tightly.

paint(card) paints one card. card.im is the color image and card.d draws on it,
card.glow and card.gd are the glow map, black where nothing glows, and
card.surface and card.rd are the surface map, roughness in green and metallic
in blue (use finish((roughness, metallic)) for its colors). card.w, card.h, and
card.rng are the size and a random generator seeded by the card's name.
"""
from atlas_painter import finish, glass, grime, joints, rebase, seams, stains, text, wash  # noqa: F401

CONCRETE = (153, 149, 138)
# (roughness, metallic) for cards that don't paint their own finish.
DEFAULT_FINISH = (.86, 0)

# name: ((width, height) in pixels, base color, what it shows)
CARDS = {
    'roof_flat': ((448, 448), (93, 101, 105), 'Flat membrane roof with seams, two drains, and weathering'),
    'apron_paved': ((512, 384), (112, 111, 104), 'Plain paved apron with slab joints, a kerb edge, and stains'),
    'wall_windows': ((448, 272), CONCRETE, 'Two-storey concrete wall with two rows of windows'),
    'wall_entrance': ((448, 272), CONCRETE, 'Two-storey concrete front: upper windows, glass doors at the center'),
    'concrete': ((192, 128), CONCRETE, 'Plain weathered concrete'),
    'foundation': ((256, 32), (119, 115, 108), 'Foundation band with joints and a dirty base'),
    'metal_dark': ((96, 64), (78, 86, 89), 'Dark structural metal'),
    'sign_blank': ((256, 48), (54, 74, 93), 'Painted sign panel with a light border'),
}

# Neutral cards in every theme's atlas.
BASE = ['roof_flat', 'apron_paved', 'concrete', 'foundation', 'metal_dark']

# lighting: a preset from rts-art.json. glow: whether the set paints a glow map.
# Optional: "fill_gaps": True, and "clean": True for spotless sets with no noise or stipple.
THEMES = {
    # 'industrial': {'lighting': 'day', 'glow': False, 'cards': ['wall_windows', 'wall_entrance', 'sign_blank']},
}

# The same settings, plus surface: whether the atlas carries a roughness and metallic map.
FACTIONS = {
    # 'vanguard': {'lighting': 'day', 'glow': True, 'surface': True, 'cards': [...]},
}


def paint(card):
    name, d, w, h = card.name, card.d, card.w, card.h

    if name == 'roof_flat':
        rebase(card, 16)
        for y in range(40, h, 64):
            d.line((0, y, w, y), fill=(80, 88, 92), width=2)
        for x, y in ((w // 4, h // 3), (3 * w // 4, 2 * h // 3)):
            d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(48, 52, 54))
        stains(card, 12)
        grime(card, [(0, 0, w, 10, 40)], 20)

    if name == 'apron_paved':
        rebase(card, 16)
        joints(d, w, h, 96, (92, 91, 85), (128, 127, 120), rows=range(96, h, 96))
        d.rectangle((0, h - 18, w, h), fill=(132, 131, 124))
        stains(card, 10)

    if name in ('wall_windows', 'wall_entrance'):
        seams(d, w, h, 76, [h // 2 - 4, h - 17])
        d.rectangle((0, h - 15, w, h), fill=(121, 120, 112))
        for x0 in (40, 168, 296):
            glass(d, x0, 40, x0 + 104, 100, 2)
        if name == 'wall_windows':
            for x0 in (40, 168, 296):
                glass(d, x0, 160, x0 + 104, 220, 2)
        else:
            glass(d, 40, 160, 120, 220, 1)
            glass(d, 164, 150, 284, h - 18, 2, door=True)
            glass(d, 328, 160, 408, 220, 1)
        grime(card, [(0, 0, w, 6, 50), (0, h - 8, w, h, 60)], 40)

    if name == 'foundation':
        joints(d, w, h, 48, (96, 93, 87), (140, 136, 128))
        grime(card, [(0, h - 10, w, h, 70)])

    if name == 'metal_dark':
        card.rd.rectangle((0, 0, w, h), fill=finish((.5, 1)))

    if name == 'sign_blank':
        d.rectangle((0, 0, w - 1, h - 1), outline=(214, 210, 196), width=3)
        text(d, (w // 2, h // 2), 'DEPOT', 30, (226, 222, 206), condensed=True)
