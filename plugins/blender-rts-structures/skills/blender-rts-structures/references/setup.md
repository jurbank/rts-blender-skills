# Set up a project

Do this once per game project, when it has no `rts-art.json`. Work through it with the user, since several steps need their answers or their editor. Templates are in the skill's `templates/` folder, and finished examples of the docs are in `examples/`.

1. **Find the project root.** In Unity it holds `Assets/` and `ProjectSettings/`. Everything below is relative to it.
2. **Find Blender.** Use `blender` on PATH, `/Applications/Blender.app/Contents/MacOS/Blender` on macOS, or `C:\Program Files\Blender Foundation\Blender <version>\blender.exe` on Windows. Blender 4.2 or newer works. Ask the user to install it from blender.org if it is missing.
3. **Write `rts-art.json`.** Copy `templates/rts-art.json` to the project root. Its paths keep Blender sources, atlases, staging, and renders in `Art/` and docs in `Docs/Art/`, beside `Assets/`, and approved models in `Assets/Art/Structures/`. Change them if the project already has a place for art. `lightUnits` is `unity` for Unity's built-in pipeline and URP, or `blender` to give strengths in Blender's own units.
4. **Match the game camera and daylight.** For Unity, follow [the Unity notes](unity.md): install glTFast, add `RtsArtSettings.cs`, and have the user run its menu item and paste the result. Merge its `camera` block and its `day` preset into `rts-art.json`, keeping `floor` close to the game's ground color. For another engine, ask for the camera's vertical field of view, its pitch below the horizon, its usual distance to the ground, and the sun's direction relative to the camera's heading. Keep the `night` preset unless the game has night maps to match.
5. **Pick the two review views.** Ask which screens players use. The template's `desktop` (1920×1080) and `handheld` (1280×800, a Steam Deck) suit a PC game. Use the smallest screen that matters as the second view.
6. **Write the art direction.** Copy `templates/docs/ART_DIRECTION.md` to `<docs>/ART_DIRECTION.md` and fill it in with the user: the overall style, what makes buildings readable from the game camera, and how themes and factions differ. `examples/ART_DIRECTION.md` is a finished one from another game. Keep the rules short and checkable, since the reviewer judges every building against them.
7. **Write the first set file.** Ask which theme or faction comes first, and write `<docs>/themes/<theme>.md` or `<docs>/factions/<faction>.md` from `templates/docs/set.md` with the user. The building-types table matters most: one row per building, each with a silhouette no other type shares. `examples/themes/` and `examples/factions/` show finished ones. Ask for inspiration images, and describe in the set file what to take from each.
8. **Start the atlas.** Copy `templates/atlas_sets.py` to `<materials>/atlas_sets.py`. Add the first set to `THEMES` or `FACTIONS`, add cards for its palette and surfaces, and paint the atlases as [the pipeline](pipeline.md) describes. The starter cards are a neutral concrete kit to replace or extend.
9. **Ignore generated files.** Add these lines to `.gitignore`, adjusted to the paths in `rts-art.json`:

   ```
   *.blend1
   *.blend@
   Art/Blender/gallery.blend
   Art/Staging/
   ```

   `.blend` files and atlases are binary, so suggest Git LFS for `*.blend`, `*.jpg`, `*.png`, and `*.glb` if the project uses Git and doesn't have it yet.
10. **Check which way models face.** Build a test box, `facing-test`, in the first set, about 4 × 4 × 3 units, with a door card on its -Y side and a roof card on top. Export it, copy it to `<runtime>/<set>/`, and ask the user to drop it into the game scene with rotation zero and look through the game camera. If the door faces away from the camera, set `export.turn` to 180 in `rts-art.json` and export again. If it faces left or right, use 90 or -90. Then delete the test source, export, and runtime copy, including any `.meta` files Unity made.

Then return to the user's request.
