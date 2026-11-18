# Blender RTS pipeline

## Locations

`<name>` is the folder `rts-art.json` gives under `paths`, relative to the project root. A structure belongs to one set: a theme, the look of a map, or a faction, the complete look of one side. `<set>` below is `themes/<theme>` or `factions/<faction>`.

| Location                                             | Contents                                                                            |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `rts-art.json`                                       | Folders, the game camera, the two review views, and the review lighting presets     |
| `<docs>/ART_DIRECTION.md`                            | Rules every set follows                                                             |
| `<docs>/themes/<theme>.md`, `<docs>/factions/<f>.md` | The set's look: shapes, palette, surfaces, glow, signage, building types            |
| `<library>/structures/<set>/<asset-id>.blend`        | Editable building and structure sources                                             |
| `<library>/units/<asset-id>.blend`                   | Future unit sources                                                                 |
| `<library>/creatures/<asset-id>.blend`               | Future creature sources                                                             |
| `<materials>/atlas_sets.py`                          | The project's atlas cards, sets, and card painting                                  |
| `<materials>/<set>/atlas.jpg`                        | A set's texture atlas that its structures map faces onto                            |
| `<materials>/<set>/atlas-glow.jpg`                   | The set's glow map, for sets that glow                                              |
| `<materials>/<set>/atlas-surface.jpg`                | The set's roughness (green) and metallic (blue) map, for sets with their own finish |
| `<materials>/<set>/atlas.json`                       | Card map and tool settings: each card's rectangle, review lighting, glow, surface   |
| `<gallery>`                                          | Generated inspection scene with relative collection links                           |
| `<staging>/<set>/<asset-id>.glb`                     | Individual exports for review                                                       |
| `<renders>/<set>/<asset-id>-review.png`              | Review sheet of a staged export from the game camera                                |
| `<runtime>/<set>/<asset-id>.glb`                     | Approved exports the game loads                                                     |

Version control tracks the sources, `atlas_sets.py` and its painted atlases, and approved runtime exports. It ignores the gallery, staging exports and renders, and Blender's `.blend1` backups because they are generated. Keep the library, materials, staging, and renders outside the engine's asset folder, such as Unity's `Assets/`, so the engine doesn't import sources or unapproved exports.

Register `<library>` once in Blender under **Preferences → File Paths → Asset Libraries** to browse all source assets. Optional Asset Browser catalogs can group entries as Structures, Units, and Creatures. Keep any catalog definition at the library root with the sources. Add unit and creature folders when their first assets exist.

The gallery arranges linked collection instances by category and structure set. Each sits on its grid point exactly as authored, so an off-center or floating asset shows. Save a source edit and reopen the gallery to see it. Rebuild the gallery to pick up additions, removals, or renamed assets. The gallery is a generated review file. Save any custom review setup under a separate filename.

## Source contract

- Use lowercase kebab-case for the asset ID. The source filename stem, marked collection name, and export filename stem match. Keep the ID stable across revisions.
- Within each set, use one canonical asset per source file, with an ordinary Blender collection named after the asset ID. Put the static visual payload in that collection and its children. Keep references, cameras, lights, collision guides, and alternate states in sibling collections. Distinct damage states or rigged objects need their own explicit export scope.
- Use one Blender unit per game world unit (one meter in Unity), +Z up, and -Y as the authoring front. Put the footprint center at the source world origin and the intended ground plane at Z=0. A foundation may sink up to 0.25 units below Z=0 to meet uneven terrain. Export allows the bounds center to drift 10% of the width or depth for overhangs. Keep the collection instance offset at zero. The GLB exporter converts to +Y up, and `export.turn` in `rts-art.json` turns the model about the vertical so its front faces the game camera once the engine imports it.
- Keep the model positioned at that anchor in the source. Clear accidental transforms and use deliberate local pivots for parts that need them. Check the dimensions against the actual gameplay footprint, including visual overhangs. Navigation and placement remain game data.
- Inspect evaluated geometry for missing faces, flipped normals, broken modifiers, unreadable details, and accidental internal or coincident surfaces. Keep hard-edge smoothing and bevels consistent with related assets.

## Textures and performance

Shipped structures carry image textures, as `ART_DIRECTION.md` asks for painted detail. Use shared flat colors and roughness values only while blocking out. Keep material slots few and combine compatible static details when it improves the exported primitive count. A Blender mesh count alone does not capture the renderer's draw work because a mesh can have several material primitives.

### Set atlases

Each set's structures share one texture, `<materials>/<set>/atlas.jpg`. It holds painted cards such as walls, roofs, rooftop equipment, metals, and signs. Every theme's atlas carries the neutral `BASE` cards plus its own. A faction's atlas holds only its own cards. Read `atlas.json` instead of viewing the image: it lists each card's pixel rectangle and what it shows, plus the set's review lighting, glow map, and surface map. A set that glows also has `atlas-glow.jpg`, black except where cards glow, which the exporter writes as an emissive texture. A set with its own finish also has `atlas-surface.jpg`, with roughness in green and metallic in blue, which the exporter writes as a metallic-roughness texture. Sets without one share a matte finish.

Map each face onto a whole card with `scripts/atlas_cards.py`. Save the new source to its library path first, so the atlas images link with relative paths. Inside Blender, add the skill's `scripts` folder to `sys.path`, then call `atlas_cards.apply(obj, {"front": "wall_entrance", "top": "roof_flat"}, default="concrete", theme="industrial")`, or pass `faction="vanguard"` instead of `theme=`. It finds the project through `rts-art.json` above the saved file. It gives the object the set's material, with its glow and surface maps when the set has them, and fits the card for each side (front, back, left, right, top, bottom) to the object's extent, so text reads correctly from outside. Pass `from_above=True` for a curved roof. Model the masses as separate objects, one per surface type, so each side can take one card. Model rounded edges as geometry rather than with a bevel modifier where the faces on either side take different cards, since the bevel blends their UVs and smears unrelated cards across the edge. For reference when mapping by hand, pixel rows count from the top, so for a card at `x`, `y` with size `w` × `h` in an atlas of `width` × `height`, U runs from `(x + 0.5) / width` to `(x + w - 0.5) / width` and V from `1 - (y + h - 0.5) / height` to `1 - (y + 0.5) / height`. Size faces so a card stretches only a little. `apply` records the card each face uses. After the atlas is repainted, call `atlas_cards.refresh(obj, theme=...)` or `refresh(obj, faction=...)` on each mesh to fit its UVs to the cards' new positions.

Reuse cards before adding any. When nothing fits, define the card in `CARDS` in `<materials>/atlas_sets.py`, paint it in `paint()` with the helpers from `scripts/atlas_painter.py`, add it to its set's list in `THEMES` or `FACTIONS`, and paint the atlases from the project root:

```sh
uv run --with pillow python "$SKILL_DIR/scripts/atlas_painter.py"
```

Without `uv`, install Pillow once with `python3 -m pip install pillow` (`py -m pip install pillow` on Windows) and run the script with that Python. Pass `--only themes/<theme>` to paint one set. Paint glow on `card.gd` beside the color, and finish on `card.rd`. Start a faction's card names with its faction ID, such as `vanguard_shell`, since `CARDS` is shared. Cards pack onto 2048-pixel pages in list order, so adding one can move others, and a new page widens the atlas. Refresh every source in that set afterward, then export again. List cards tallest first so they pack tightly. Add a new set to `THEMES` or `FACTIONS` with its settings, next to its file in `<docs>`. Mark a spotless set `"clean": True` to skip the painted noise. Signs need real font rendering, which is why Pillow is used; `fonts` in `rts-art.json` can name font files, and otherwise the painter takes the first bold system font it finds. Do any other image work with the Python and numpy that ship with Blender, not a separate environment.

Use deliberate UVs and consistent texel density within the set. Use sRGB for base color and emissive maps, and non-color data for normals and metallic/roughness. Bake procedural shaders that the exporter cannot represent into glTF-compatible maps. The render command re-imports the GLB, so its renders show whether the expected images survived export. Keep authoring texture sizes separate from delivery sizes, which the engine's import settings can reduce. Choose export sizes through visual comparison at game zoom.

When evaluating an export, inspect it at target zoom and with the expected number of copies in view. Reduce invisible geometry, expensive transparency, and material fragmentation first. Add LODs when a representative scene demonstrates a need and the engine supports them. Putting a GLB in the runtime folder makes it an asset. Placing it in the game, with its prefab, collider, and footprint, is separate work.

## Background helper

Run from the project root. Replace `$SKILL_DIR` with the full path to this skill directory. Use the installed Blender executable if `blender` is not on PATH: `/Applications/Blender.app/Contents/MacOS/Blender` on macOS, or `"C:\Program Files\Blender Foundation\Blender <version>\blender.exe"` on Windows.

Build the gallery after your first asset is saved.

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python "$SKILL_DIR/scripts/blender_assets.py" -- gallery
```

Export a static structure by its ID and set. Export and render require `--theme` or `--faction`.

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python "$SKILL_DIR/scripts/blender_assets.py" -- export barracks --faction vanguard
```

All commands accept `--root /path/to/project` after the subcommand, and otherwise find `rts-art.json` in the current folder or above it. Gallery and export refuse to overwrite by default. Pass `--replace` when refreshing the intended generated output. Export uses a clean Blender process, appends the named collection, turns it by `export.turn`, and writes a standalone GLB to staging. Its static payload allows meshes and ordinary transform empties within the collection. Export fails when the GLB has no image textures, links images outside the file, or lacks an emissive texture in a set that glows. Pass `--blockout` to stage an untextured blockout. Check moving parts, animation, and non-mesh content through a purpose-built export. Copy a GLB to the runtime folder only after the user approves it.

Render a staged export for review, lined up with its closest neighbors.

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python "$SKILL_DIR/scripts/blender_assets.py" -- render depot --theme industrial --with barracks,refinery
```

Render imports the staged GLB, not the source, turns it back by `export.turn`, and lights it with the set's review lighting from its `atlas.json`, or with `--lighting <preset>` naming any preset in `rts-art.json`. Each preset is a sky and ground hemisphere, a sun, and a ground color, in Unity's units when `lightUnits` is `unity`. A faction can stand on any map, so render it by day and by night. A lighting other than the set's default writes `<asset-id>-<lighting>-review.png` beside the default sheet. The camera uses `camera` in `rts-art.json`: its vertical field of view and its pitch below the horizon, with the front facing the camera. `--with` takes neighbor IDs in the selected set and uses their approved runtime exports, falling back to staged ones. Line up buildings from the same set. A `theme/id` or `factions/<faction>/id` reference reaches another set, for comparing scale only.

It writes `<asset-id>-review.png`, a single 1400-pixel-wide sheet for review:

- Top left: a close view for checking texture detail.
- Top right: the lineup, with the asset first and the neighbors to its right in the order given.
- Bottom left and right: crops of the two `views` in `rts-art.json`, a large screen first and a small one second, at true pixel size.

Both views use the same camera distance, `camera.distance`, so the two crops show how many fewer pixels the building gets on the small screen. Pass `--distance` to try other zoom levels. The full close and view renders sit beside the sheet for a closer look. Review from the sheet. Each render replaces the previous one. The renders approximate the game's look. The real check is the game.
