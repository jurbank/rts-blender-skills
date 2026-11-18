# Art direction

<!-- One or two sentences on the overall style. For example: "Lower poly because it's an RTS, but not the trendy low-poly look." -->

Structures come in two kinds of set. A **theme** is the look of a map: its lighting, ground, and civic buildings, which belong to the map whoever holds them. A **faction** is the look of one side's buildings and units, and it is complete on its own. A match has one theme, and each player picks a faction, so any faction can appear on any theme's map. A theme never refers to a faction, and a faction never refers to a theme or another faction.

These rules hold in every set. Each theme's look lives in `themes/<theme>.md` and each faction's in `factions/<faction>.md` beside this file, and both build on these rules and may not break them. Inspiration images live in `inspiration/<theme>/` and `inspiration/factions/<faction>/`, and each set's file describes in words what to take from them. Take the look, not the setting, factions, buildings, logos, or UI.

## Readability

- **Detail comes from textures.** Forms are simple masses with soft bevels. Windows, panel lines, vents, signs, and wear are painted, not modeled.
- **Roofs identify buildings.** From the game camera the roof is most of what a player sees, so the roof says what the building is for.
- **Small screens get the same match.** A building still reads by silhouette on the smallest screen the game supports, and fine detail doesn't turn into noise.
- **Team colors stay identifiable.** Team colors, selection rings, and effects are the most saturated things on screen. A building's accents and glow stay small and below team colors in saturation, within the limits of its set.

<!-- Add the game's own readability rules here. -->

## Buildings

- **Each building type looks unique within its set.** Its silhouette and massing differ from every other type in its theme or faction, so a player can tell them apart by shape alone. Shapes repeat only across designated variants of one type.
- **Accents are the set's choice.** Each set decides whether its building types carry accent colors, and lists them in its file.
- **Footprints come from the game.** A building keeps the gameplay footprint from its game definition in every set. Only its look changes.

## Factions

- **A faction is complete on its own.** Its file sets its shape language, materials, surface finish, palette, glow, signage, and emblem, and its building types, with no reference to any theme or other faction.
- **A faction reads on every map.** It must read by shape in daylight and keep its own look under any theme's lighting, so its review renders both day and night.
- **Factions differ by shape first.** Players learn each faction's buildings, so a faction's version of a role needn't share a cue with another faction's.

## Set files

Each theme file has these sections: Identity, Shape language, Materials, Palette, Glow, Lighting, Signage, Building types, References, and Avoid. Building types is a table with each type's signature silhouette feature, accent color, and required elements.

Each faction file has the same sections, with Surfaces in place of Lighting: how matte, glossy, or metallic each material is, since a faction brings its own finish to every map. Building types is a table with each type's signature silhouette feature and required elements, plus accents if the faction uses them.

Tool settings for each set, such as its review lighting or surface finish, sit with its atlas in `atlas_sets.py`.

<!-- List each set with a one-line description, linking its file. -->
