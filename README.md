# RTS Blender skills

A Claude Code plugin for making RTS buildings in Blender. Claude models each building to a written art direction, textures it from a painted atlas shared by its theme or faction, exports a game-ready GLB, and renders a review sheet from your game's camera. A separate reviewer agent then judges the sheet before you see it. It's set up for Unity, and `rts-art.json` adapts it to other engines.

## What you need

- The Claude desktop app (Code tab) or Claude Code in a terminal
- [Blender](https://www.blender.org/download/) 4.2 or newer
- Python 3 with Pillow, or [uv](https://docs.astral.sh/uv/), to paint the texture atlases
- For Unity: the glTFast package (`com.unity.cloud.gltfast`), added through the Package Manager

## Install

Run these once in a terminal. The plugin is then available in every Claude Code session, including the desktop app's Code tab.

```sh
claude plugin marketplace add jurbank/rts-blender-skills
```

```sh
claude plugin install blender-rts-structures@rts-blender
```

To install from a downloaded copy instead, pass its folder: `claude plugin marketplace add /path/to/rts-blender-skills`.

## First use

Open your game project's folder in the Code tab and ask for a building, for example *"Make a barracks for my human faction."* Claude sees that the project isn't set up and walks you through it first:

1. It writes `rts-art.json` at the project root, with the folders it will use. Blender sources stay in `Art/`, beside `Assets/`, and only approved models go into `Assets/Art/Structures/`.
2. It adds a small editor script. You run **Tools → RTS Art → Copy Review Settings** in Unity and paste the result into the chat, so the review renders match your camera and lighting.
3. It writes `Docs/Art/ART_DIRECTION.md` and your first theme or faction file with you. These say what your buildings should look like, and the reviewer checks every building against them. The skill's `examples/` folder has finished ones from another game.
4. It paints a starter texture atlas for that set.
5. It exports a test box so you can check that buildings face your camera in Unity.

After that, each building takes one request. Claude blocks it out, shows you a review sheet, textures it, has it reviewed, and leaves it in `Art/Staging/` until you approve it.

## Update

```sh
claude plugin marketplace update rts-blender
```

```sh
claude plugin update blender-rts-structures@rts-blender
```

## What's inside

```
plugins/blender-rts-structures/
  agents/structure-reviewer.md       the reviewer, which only reads
  skills/blender-rts-structures/
    SKILL.md                         the workflow Claude follows
    references/                      pipeline, review, setup, and Unity notes
    scripts/                         Blender export and render, card mapping, atlas painter
    templates/                       rts-art.json, atlas_sets.py, doc templates, the Unity editor script
    examples/                        finished art direction and set files, and demo models with review sheets
```
