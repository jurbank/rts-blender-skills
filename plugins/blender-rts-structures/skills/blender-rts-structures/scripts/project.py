"""Find the project's rts-art.json and resolve its settings.

Every script in this folder reads the project through here, so paths, the game
camera, and review lighting live in one file at the project root.
"""
import json
import math
from pathlib import Path

CONFIG = "rts-art.json"
PATH_KEYS = ("docs", "library", "materials", "gallery", "staging", "renders", "runtime")
LIGHT_KEYS = ("sky", "ground", "ambientIntensity", "sun", "sunIntensity", "sunFrom", "floor")
# Blender's sun lights a white surface facing it to 1/pi of its strength. Unity's built-in
# and URP lights light it to their full intensity. Ambient light matches in both.
SUN_SCALE = {"unity": math.pi, "blender": 1.0}


class Project:
    def __init__(self, root, settings):
        self.root = root
        self.settings = settings
        self.paths = {key: root / settings["paths"][key] for key in PATH_KEYS}
        camera = settings["camera"]
        self.field_of_view = float(camera["fieldOfView"])
        self.pitch = float(camera["pitch"])
        self.distance = float(camera.get("distance", 30))
        self.min_distance = float(camera.get("minDistance", 8))
        self.turn = float(settings.get("export", {}).get("turn", 0))
        self.views = settings["views"]
        self.fonts = settings.get("fonts", {})

    def lighting(self, name):
        presets = self.settings["lighting"]
        if name not in presets:
            raise ValueError(f"{CONFIG} has no lighting preset {name!r}. It has {', '.join(sorted(presets))}")
        preset = presets[name]
        missing = [key for key in LIGHT_KEYS if key not in preset]
        if missing:
            raise ValueError(f"Lighting preset {name!r} in {CONFIG} is missing {', '.join(missing)}")
        units = self.settings.get("lightUnits", "unity")
        if units not in SUN_SCALE:
            raise ValueError(f"lightUnits in {CONFIG} must be one of {', '.join(SUN_SCALE)}, got {units!r}")
        sun_from = preset["sunFrom"]
        return {
            **preset,
            "sky_strength": float(preset["ambientIntensity"]),
            "sun_strength": float(preset["sunIntensity"]) * SUN_SCALE[units],
            # Review space looks at the front from -Y with +Z up, so toward the camera is -Y.
            "sun_direction": (sun_from["right"], -sun_from["towardCamera"], sun_from["up"]),
        }

    def lighting_names(self):
        return sorted(self.settings["lighting"])


def find_root(start=None):
    """The nearest folder at or above `start` that holds rts-art.json."""
    here = Path(start or Path.cwd()).resolve()
    for folder in (here, *here.parents):
        if (folder / CONFIG).is_file():
            return folder
    raise ValueError(
        f"No {CONFIG} in {here} or any folder above it. Run from the game project, pass --root, "
        "or set the project up as the skill's references/setup.md describes."
    )


def load(root=None):
    root = find_root(root)
    settings = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    missing = [key for key in ("paths", "camera", "views", "lighting") if key not in settings]
    missing += [f"paths.{key}" for key in PATH_KEYS if key not in settings.get("paths", {})]
    if missing:
        raise ValueError(f"{root / CONFIG} is missing {', '.join(missing)}")
    if len(settings["views"]) != 2:
        raise ValueError(f"{CONFIG} needs exactly two views, a large screen and a small one, for the review sheet")
    return Project(root, settings)
