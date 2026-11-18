"""Build a linked review gallery, stage one static structure GLB, or render a staged GLB for review.

Paths, the game camera, and review lighting come from the project's rts-art.json.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
from tempfile import TemporaryDirectory

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector
import numpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project as projects  # noqa: E402

# The review sheet: a close view and a lineup on top, crops of the two configured views at true pixel size below.
SHEET_WIDTH = 1400
SHEET_GAP = 8
SHEET_ROW = 512
SHEET_CROP_HEIGHT = 400
SHEET_BACKGROUND = "#11151a"
CROP_WIDTH = (SHEET_WIDTH - SHEET_GAP) // 2
# A set is a theme, the look of a map, or a faction, the look of one side. Each has its own folder and atlas.
THEMES = Path("themes")
FACTIONS = Path("factions")
CATEGORIES = ("structures", "units", "creatures")
ASSET_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# A foundation may sink this far below Z=0 to meet uneven terrain.
GROUND_SKIRT = 0.25
# The footprint center may drift this fraction of the asset's width or depth, for overhangs.
CENTER_TOLERANCE = 0.1
TEXTURE_KEY = re.compile(r'"\w+Texture"')


def asset_id(value):
    if not ASSET_ID.fullmatch(value):
        raise argparse.ArgumentTypeError(f"Expected a lowercase kebab-case asset ID, got {value!r}")
    return value


def structure_ref(value, default_set):
    """An ID in the default set, a theme/ID, or factions/<faction>/ID."""
    parts = value.split("/")
    if len(parts) == 1:
        return default_set, asset_id(parts[0])
    if len(parts) == 2:
        return THEMES / asset_id(parts[0]), asset_id(parts[1])
    if len(parts) == 3 and parts[0] in ("themes", "factions"):
        return Path(parts[0]) / asset_id(parts[1]), asset_id(parts[2])
    raise argparse.ArgumentTypeError(f"Expected ID, theme/ID, or factions/<faction>/ID, got {value!r}")


def load_asset(source, *, link):
    if not source.is_file():
        raise ValueError(f"Missing source file: {source}")

    with bpy.data.libraries.load(str(source), link=link, assets_only=True) as (available, result):
        if source.stem not in available.collections:
            raise ValueError(f"{source} needs a collection named {source.stem!r} marked as an Asset")
        result.collections = [source.stem]

    collection = result.collections[0]
    if collection is None:
        raise ValueError(f"Blender could not load the asset from {source}")
    if collection.instance_offset.length > 0.00001:
        raise ValueError(f"Set the collection instance offset to zero in {source}")
    return collection


def mesh_corners(obj, matrix):
    if obj.type != "MESH" or not obj.data.vertices:
        return []
    return [matrix @ Vector(corner) for corner in obj.bound_box]


def bounds(corners, label):
    if not corners:
        raise ValueError(f"{label} has no geometry")
    minimum = Vector(tuple(min(point[axis] for point in corners) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in corners) for axis in range(3)))
    return minimum, maximum


def turn(objects, degrees):
    """Turn objects about the vertical axis through the origin, moving only those without a parent."""
    if not degrees:
        return
    rotation = Matrix.Rotation(math.radians(degrees), 4, "Z")
    for obj in objects:
        if obj.parent is None:
            obj.matrix_world = rotation @ obj.matrix_world
    bpy.context.view_layer.update()


def build_gallery(project, output, destination):
    library = project.paths["library"]
    scene = bpy.context.scene
    groups = {}
    folders = [(category, library / category) for category in CATEGORIES]
    for kind in (THEMES, FACTIONS):
        sets = library / "structures" / kind
        if sets.is_dir():
            folders.extend(
                (f"structures/{kind.as_posix()}/{asset_id(folder.name)}", folder)
                for folder in sorted(sets.iterdir())
                if folder.is_dir()
            )
    for category, folder in folders:
        instances = []
        for source in sorted(folder.glob("*.blend")):
            asset_id(source.stem)
            collection = load_asset(source, link=True)
            instance = bpy.data.objects.new(f"{category}/{collection.name}", None)
            instance.instance_type = "COLLECTION"
            instance.instance_collection = collection
            instances.append(instance)
        if instances:
            display = bpy.data.collections.new(category.replace("/", " · ").title())
            scene.collection.children.link(display)
            for instance in instances:
                display.objects.link(instance)
            groups[category] = instances

    if not groups:
        raise ValueError(f"No asset source files found under {library}")

    # Measure through the instances so modifiers and object transforms count.
    bpy.context.view_layer.update()
    corners = {instance.name: [] for group in groups.values() for instance in group}
    for item in bpy.context.evaluated_depsgraph_get().object_instances:
        if item.is_instance and item.parent is not None and item.parent.name in corners:
            corners[item.parent.name] += mesh_corners(item.object, item.matrix_world)
    measured = [bounds(points, name) for name, points in corners.items()]

    # Each asset sits on its grid point as authored, so anchor mistakes stay visible.
    reach = max(max(-low.x, high.x, -low.y, high.y) for low, high in measured)
    height = max(high.z for _, high in measured)
    spacing = max(1.0, reach * 3)
    columns = math.ceil(math.sqrt(len(measured)))
    row = 0
    for group in groups.values():
        for index, instance in enumerate(group):
            instance.location = ((index % columns) * spacing, -(row + index // columns) * spacing, 0)
            instance.empty_display_size = spacing * 0.1
        row += math.ceil(len(group) / columns) + 1

    used_columns = min(columns, max(len(group) for group in groups.values()))
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.shading.color_type = "TEXTURE"
                view.overlay.show_floor = False
                view.overlay.show_axis_x = False
                view.overlay.show_axis_y = False
                view.region_3d.view_rotation = Vector((-0.65, 1.0, -1.25)).to_track_quat("-Z", "Y")
                view.region_3d.view_location = (
                    (used_columns - 1) * spacing / 2,
                    -(row - 2) * spacing / 2,
                    height / 3,
                )
                view.region_3d.view_distance = spacing * max(used_columns, row - 1) * 1.3
                view.region_3d.view_perspective = "ORTHO"

    # Set paths after linking all assets. Loading another library can normalize existing paths.
    for group in groups.values():
        for instance in group:
            source = instance.instance_collection.library
            relative = os.path.relpath(source.filepath, destination.parent)
            source.filepath = "//" + Path(relative).as_posix()
    bpy.ops.wm.save_as_mainfile(filepath=str(output), relative_remap=False)
    return f"{len(measured)} linked assets"


def glb_summary(output):
    with output.open("rb") as stream:
        magic, version, length = struct.unpack("<4sII", stream.read(12))
        json_length, chunk_type = struct.unpack("<I4s", stream.read(8))
        if (magic, version, length, chunk_type) != (b"glTF", 2, output.stat().st_size, b"JSON"):
            raise ValueError("Invalid GLB header")
        document = json.loads(stream.read(json_length))

    primitives = [primitive for mesh in document.get("meshes", []) for primitive in mesh["primitives"]]
    if not primitives or any(primitive.get("mode", 4) != 4 for primitive in primitives):
        raise ValueError("Expected a GLB with triangle primitives")
    accessors = document["accessors"]
    triangles = sum(
        accessors[primitive.get("indices", primitive["attributes"]["POSITION"])]["count"] // 3
        for primitive in primitives
    )
    if not triangles:
        raise ValueError("The exported model has no triangles")

    images = document.get("images", [])
    external = [image["uri"] for image in images if "uri" in image]
    if external:
        raise ValueError(f"The GLB references images outside the file: {', '.join(external)}")
    materials = document.get("materials", [])
    textured = sum(1 for material in materials if TEXTURE_KEY.search(json.dumps(material)))
    glowing = sum(1 for material in materials if "emissiveTexture" in material)
    summary = (
        f"{length:,} bytes, {triangles:,} triangles in mesh data, {len(primitives)} primitives, "
        f"{len(images)} images, {textured} of {len(materials)} materials textured, {glowing} glowing"
    )
    return summary, len(images), glowing


def set_settings(project, structure_set):
    path = project.paths["materials"] / structure_set / "atlas.json"
    if not path.is_file():
        raise ValueError(
            f"No atlas for {structure_set.as_posix()} at {path}. Add the set to THEMES or FACTIONS in "
            f"{project.paths['materials'] / 'atlas_sets.py'} and paint the atlases"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def export_structure(project, structure_set, identifier, output, blockout):
    source = project.paths["library"] / "structures" / structure_set / f"{identifier}.blend"
    collection = load_asset(source, link=False)
    objects = set(collection.all_objects)
    bpy.context.scene.collection.children.link(collection)
    bpy.context.view_layer.update()

    for obj in objects:
        if (
            obj.type not in {"MESH", "EMPTY"}
            or obj.instance_type != "NONE"
            or obj.animation_data
            or (obj.parent is not None and obj.parent not in objects)
        ):
            raise ValueError(f"{obj.name} requires a specialized export or belongs outside the asset collection")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = [obj.evaluated_get(depsgraph) for obj in objects]
    minimum, maximum = bounds(
        [corner for obj in evaluated for corner in mesh_corners(obj, obj.matrix_world)], identifier
    )
    if not -GROUND_SKIRT - 0.001 <= minimum.z <= 0.001:
        raise ValueError(
            f"Expected the lowest point between Z={-GROUND_SKIRT:g} and Z=0, measured Z={minimum.z:g}"
        )
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    if abs(center.x) > extent.x * CENTER_TOLERANCE or abs(center.y) > extent.y * CENTER_TOLERANCE:
        raise ValueError(
            f"Center the footprint on the world origin, measured center X={center.x:g} Y={center.y:g}"
        )

    # Turn the model so its front faces the game camera once the engine imports it.
    turn(objects, project.turn)
    status = bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_yup=True,
        export_animations=False,
        export_apply=True,
    )
    if "FINISHED" not in status:
        raise ValueError("Blender could not export the collection")
    summary, images, glowing = glb_summary(output)
    direction = project.paths["docs"] / "ART_DIRECTION.md"
    if not images and not blockout:
        raise ValueError(
            f"The export has no image textures. {direction} calls for painted detail, and "
            "procedural shaders do not survive export, so bake them. Pass --blockout to stage an untextured blockout."
        )
    if set_settings(project, structure_set)["glow"] and not glowing and not blockout:
        raise ValueError(
            f"{structure_set.as_posix()} glows, but the export has no emissive texture. Map it with atlas_cards.py, "
            "whose material links the set's glow map."
        )
    size = " × ".join(f"{value:.3g}" for value in extent)
    stage = ", untextured blockout" if blockout else ""
    return f"{summary}, {size} Blender units (width × depth × height){stage}"


def linear(color):
    channels = (int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels) + (1.0,)


def stage_like_game(scene, preset):
    """Light the scene with a review preset from rts-art.json: a sky and ground hemisphere and a sun."""
    world = bpy.data.worlds.new("Game hemisphere")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    direction = nodes.new("ShaderNodeTexCoord")
    axes = nodes.new("ShaderNodeSeparateXYZ")
    height = nodes.new("ShaderNodeMapRange")
    height.inputs["From Min"].default_value = -1
    sky = nodes.new("ShaderNodeMix")
    sky.data_type = "RGBA"
    sky.inputs["A"].default_value = linear(preset["ground"])
    sky.inputs["B"].default_value = linear(preset["sky"])
    background = nodes["Background"]
    background.inputs["Strength"].default_value = preset["sky_strength"]
    links.new(direction.outputs["Generated"], axes.inputs["Vector"])
    links.new(axes.outputs["Z"], height.inputs["Value"])
    links.new(height.outputs["Result"], sky.inputs["Factor"])
    links.new(sky.outputs["Result"], background.inputs["Color"])
    scene.world = world

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = preset["sun_strength"]
    sun.data.color = linear(preset["sun"])[:3]
    sun.rotation_euler = Vector(preset["sun_direction"]).to_track_quat("Z", "Y").to_euler()
    scene.collection.objects.link(sun)

    ground_material = bpy.data.materials.new("Ground")
    ground_material.use_nodes = True
    # A plain matte ground, so it has no reflections.
    surface = ground_material.node_tree.nodes["Principled BSDF"]
    surface.inputs["Base Color"].default_value = linear(preset["floor"])
    surface.inputs["Roughness"].default_value = 1
    surface.inputs["Specular IOR Level"].default_value = 0
    plane = bpy.data.meshes.new("Ground")
    plane.from_pydata([(-500, -500, 0), (500, -500, 0), (500, 500, 0), (-500, 500, 0)], [], [(0, 1, 2, 3)])
    plane.materials.append(ground_material)
    scene.collection.objects.link(bpy.data.objects.new("Ground", plane))

    engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = next(e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES") if e in engines)
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"


def import_glb(path, degrees):
    """Import an export and turn it back by the export turn, so its front faces the review camera."""
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = [obj for obj in bpy.context.scene.objects if obj not in before]
    turn(objects, -degrees)
    corners = [corner for obj in objects for corner in mesh_corners(obj, obj.matrix_world)]
    return objects, *bounds(corners, path.stem)


def find_export(project, structure_set, identifier):
    for folder in ("runtime", "staging"):
        path = project.paths[folder] / structure_set / f"{identifier}.glb"
        if path.is_file():
            return path
    raise ValueError(
        f"No export of {identifier} in {project.paths['runtime'] / structure_set} "
        f"or {project.paths['staging'] / structure_set}"
    )


def shoot(scene, camera, pitch, target_x, away, width, height, path, *, target_z=0.0):
    pitch = math.radians(pitch)
    camera.location = (target_x, -away * math.cos(pitch), target_z + away * math.sin(pitch))
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def read_png(path):
    image = bpy.data.images.load(str(path))
    width, height = image.size
    pixels = numpy.empty(width * height * 4, dtype=numpy.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    # Blender stores rows bottom up. Arrays here run top down.
    return numpy.flipud(pixels.reshape(height, width, 4))


def write_png(array, path):
    height, width = array.shape[:2]
    image = bpy.data.images.new("Review sheet", width, height, alpha=False)
    image.pixels.foreach_set(numpy.ascontiguousarray(numpy.flipud(array)).ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()


def asset_crop(scene, camera, minimum, maximum, pixels, limit):
    """Crop a render around the asset at its true pixel size, padded and capped at `limit`."""
    height, width = pixels.shape[:2]
    corners = [Vector((x, y, z)) for x in (minimum.x, maximum.x) for y in (minimum.y, maximum.y) for z in (minimum.z, maximum.z)]
    points = [world_to_camera_view(scene, camera, corner) for corner in corners]
    left, right = min(p.x for p in points) * width, max(p.x for p in points) * width
    top, bottom = (1 - max(p.y for p in points)) * height, (1 - min(p.y for p in points)) * height
    pad = max(16, 0.25 * max(right - left, bottom - top))
    crop_width = min(limit[0], width, round(right - left + 2 * pad))
    crop_height = min(limit[1], height, round(bottom - top + 2 * pad))
    x = min(max(0, round((left + right - crop_width) / 2)), width - crop_width)
    y = min(max(0, round((top + bottom - crop_height) / 2)), height - crop_height)
    return pixels[y:y + crop_height, x:x + crop_width]


def render_structure(project, structure_set, identifier, neighbors, distance, lighting):
    """Render the staged GLB, not the source, so anything the exporter dropped shows."""
    source = project.paths["staging"] / structure_set / f"{identifier}.glb"
    if not source.is_file():
        raise ValueError(f"Export {identifier} before rendering it. Missing {source}")
    scene = bpy.context.scene
    _, minimum, maximum = import_glb(source, project.turn)

    # Line neighbors up to the right of the asset, left to right in the order given.
    lineup = [(minimum, maximum)]
    hidden = []
    edge, gap = maximum.x, max(1.0, (maximum - minimum).x * 0.3)
    for neighbor_set, neighbor in neighbors:
        objects, low, high = import_glb(find_export(project, neighbor_set, neighbor), project.turn)
        shift = edge + gap - low.x
        for obj in objects:
            if obj.parent is None:
                obj.location.x += shift
            obj.hide_render = True
        hidden += objects
        lineup.append((low + Vector((shift, 0, 0)), high + Vector((shift, 0, 0))))
        edge = high.x + shift
    default = set_settings(project, structure_set)["lighting"]
    stage_like_game(scene, project.lighting(lighting or default))

    field_of_view, pitch_degrees = project.field_of_view, project.pitch
    camera = bpy.data.objects.new("Game camera", bpy.data.cameras.new("Game camera"))
    camera.data.sensor_fit = "VERTICAL"
    camera.data.angle_y = math.radians(field_of_view)
    camera.data.clip_end = 2000
    camera.rotation_euler = (math.radians(90 - pitch_degrees), 0, 0)
    scene.collection.objects.link(camera)
    scene.camera = camera

    # Every view looks at the front (-Y) from above it, as the game camera does at its default heading.
    half_angle = math.tan(math.radians(field_of_view) / 2)
    reach = (maximum - minimum).length / 2
    close = max(project.min_distance, reach / math.sin(math.radians(field_of_view) / 2) * 1.15)
    folder = project.paths["renders"] / structure_set
    folder.mkdir(parents=True, exist_ok=True)
    # A lighting other than the set's default gets its own files, so both sheets can sit side by side.
    stem = identifier if lighting in (None, default) else f"{identifier}-{lighting}"
    views = project.views
    path = {name: folder / f"{stem}-{name}.png" for name in ("close", "review", *(view["name"] for view in views))}
    shoot(scene, camera, pitch_degrees, 0, close, 1024, 1024, path["close"], target_z=(minimum.z + maximum.z) / 2)
    crops = []
    for view in views:
        shoot(scene, camera, pitch_degrees, 0, distance, view["width"], view["height"], path[view["name"]])
        pixels = read_png(path[view["name"]])
        crops.append(asset_crop(scene, camera, minimum, maximum, pixels, (CROP_WIDTH, SHEET_CROP_HEIGHT)))

    for obj in hidden:
        obj.hide_render = False
    left, right = lineup[0][0].x, lineup[-1][1].x
    target_x = (left + right) / 2
    lineup_width = SHEET_WIDTH - SHEET_ROW - SHEET_GAP
    horizontal = half_angle * lineup_width / SHEET_ROW
    pitch = math.radians(pitch_degrees)
    rise, run = math.sin(pitch), math.cos(pitch)
    away = project.min_distance
    # Fit all bounds corners in the perspective frustum, including tall near edges.
    for low, high in lineup:
        across = max(abs(low.x - target_x), abs(high.x - target_x))
        for y in (low.y, high.y):
            for z in (low.z, high.z):
                up = abs(y * rise + z * run)
                depth_offset = y * run - z * rise
                away = max(away, max(across / horizontal, up / half_angle) / 0.92 - depth_offset)
    with TemporaryDirectory() as temporary:
        lineup_path = Path(temporary) / "lineup.png"
        shoot(scene, camera, pitch_degrees, target_x, away, lineup_width, SHEET_ROW, lineup_path)
        lineup_pixels = read_png(lineup_path)

    sheet = numpy.empty((SHEET_ROW + SHEET_GAP + max(len(crop) for crop in crops), SHEET_WIDTH, 4), numpy.float32)
    sheet[:] = [int(SHEET_BACKGROUND[i:i + 2], 16) / 255 for i in (1, 3, 5)] + [1]
    halved = read_png(path["close"]).reshape(SHEET_ROW, 2, SHEET_ROW, 2, 4).mean(axis=(1, 3))
    sheet[:SHEET_ROW, :SHEET_ROW] = halved
    sheet[:SHEET_ROW, SHEET_ROW + SHEET_GAP:] = lineup_pixels
    below = SHEET_ROW + SHEET_GAP
    for index, crop in enumerate(crops):
        start = index * (CROP_WIDTH + SHEET_GAP)
        sheet[below:below + len(crop), start:start + crop.shape[1]] = crop
    write_png(sheet, path["review"])
    return [str(path[name]) for name in ("review", "close", *(view["name"] for view in views))]


def main():
    if not bpy.app.background:
        raise SystemExit("Run this helper with Blender's --background flag")

    arguments = argparse.ArgumentParser(description=__doc__)
    commands = arguments.add_subparsers(dest="command", required=True)
    for command in (commands.add_parser("gallery"), commands.add_parser("export")):
        command.add_argument("--replace", action="store_true", help="Replace the generated output")
    commands.choices["export"].add_argument("asset_id", type=asset_id)
    commands.choices["export"].add_argument(
        "--blockout", action="store_true", help="Allow an untextured export for shape review"
    )
    render = commands.add_parser("render", help="Render a staged export from the game camera")
    render.add_argument("asset_id", type=asset_id)
    for command in (commands.choices["export"], render):
        which = command.add_mutually_exclusive_group(required=True)
        which.add_argument("--theme", type=asset_id, help="A theme, the look of a map")
        which.add_argument("--faction", type=asset_id, help="A faction, the look of one side")
    render.add_argument(
        "--with",
        dest="neighbors",
        default="",
        help="Comma-separated IDs in the same set, theme/ID, or factions/<faction>/ID references to approved or "
        "staged structures",
    )
    render.add_argument("--lighting", help="A lighting preset from rts-art.json, instead of the set's default")
    render.add_argument("--distance", type=float, help="Camera distance for the two view crops")
    for command in commands.choices.values():
        command.add_argument("--root", type=Path, help="The game project, if not the current folder or above it")
    options = arguments.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    try:
        project = projects.load(options.root)
    except ValueError as error:
        arguments.error(str(error))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if options.command != "gallery":
        structure_set = THEMES / options.theme if options.theme else FACTIONS / options.faction

    if options.command == "render":
        if options.lighting and options.lighting not in project.lighting_names():
            render.error(f"--lighting must be one of {', '.join(project.lighting_names())} from rts-art.json")
        try:
            neighbors = [
                structure_ref(item.strip(), structure_set) for item in options.neighbors.split(",")
            ] if options.neighbors else []
        except argparse.ArgumentTypeError as error:
            render.error(str(error))
        print("\n".join(render_structure(
            project, structure_set, options.asset_id, neighbors,
            options.distance or project.distance, options.lighting,
        )))
        return
    if options.command == "gallery":
        destination = project.paths["gallery"]
    else:
        destination = project.paths["staging"] / structure_set / f"{options.asset_id}.glb"

    if not options.replace and destination.exists():
        arguments.error(f"{destination} already exists. Pass --replace to overwrite it.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as temporary:
        output = Path(temporary) / destination.name
        if options.command == "gallery":
            summary = build_gallery(project, output, destination)
        else:
            summary = export_structure(project, structure_set, options.asset_id, output, options.blockout)
        if options.replace:
            output.replace(destination)
        else:
            os.link(output, destination)

    print(f"{destination} ({summary})")


if __name__ == "__main__":
    main()
