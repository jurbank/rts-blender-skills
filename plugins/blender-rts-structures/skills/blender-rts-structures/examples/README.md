# Examples

Finished art direction and set files from a web RTS built with this pipeline. They show the level of detail that gives the reviewer something to check: a building-types table where every row has its own silhouette, palettes with hex colors, and an Avoid list. Their paths, phone views, and mentions of `city_atlas.py` belong to that game. Use the templates for a new project.

## Demo models

`models/toxic-industrial/` holds three finished buildings for the [toxic industrial](factions/toxic-industrial.md) faction, each as a game-ready GLB beside its review sheet from the game camera. They passed the reviewer and show what a finished building looks like: one primitive each, with the faction's atlas, glow, and roughness and metallic maps embedded.

| Model | What it shows | Triangles | Size (width × depth × height) |
| ----- | ------------- | --------- | ----------------------------- |
| `supply-depot.glb` | Three capsule tanks half sunk into a sloped concrete berm, a pipe rack over a three-bay drop-off pad | 1,460 | 4 × 4 × 2.47 |
| `refinery.glb` | Two process columns rising from a concrete furnace block on a berm, a flare stack, a glowing sludge pool | 1,440 | 4.8 × 4.8 × 2.87 |
| `war-factory.glb` | A sawtooth-roofed hall with a control block cantilevered over a furnace-lit blast door and two crest banners | 296 | 4.5 × 5.6 × 2.96 |

Each stands in a walled compound with razor wire and a slag heap. Sizes are in game units with the front facing -Y in Blender, +Z in the GLB. Open a GLB in Blender, a glTF viewer, or Unity with glTFast to look around it.
