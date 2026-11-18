# Unity notes

## Import GLB files

Unity doesn't import glTF on its own. Install glTFast, Unity's glTF importer: **Window → Package Manager → + → Add package by name**, then `com.unity.cloud.gltfast`. After that, a `.glb` copied into `Assets/` imports as a model you can drag into a scene or a prefab. glTFast picks shaders for the built-in pipeline, URP, or HDRP, and keeps the atlas's base color, emissive glow, and metallic-roughness maps. If the project already uses UnityGLTF, that works too.

Keep `.blend` files out of `Assets/`. Unity tries to import them by running Blender, which is slow and loses the pipeline's checks. The default `rts-art.json` keeps them in `Art/` beside `Assets/`.

Unity makes a `.meta` file beside each imported GLB. Commit it with the GLB, and delete it with the GLB.

## Match the camera and lighting

Copy `templates/unity/RtsArtSettings.cs` into `Assets/Editor/` (make the folder if needed). It needs Unity 2022.2 or newer. Ask the user to:

1. Open the scene with the game camera and the sun, with the camera tagged `MainCamera`.
2. Set the camera's angle and zoom as they are in a typical match.
3. Choose **Tools → RTS Art → Copy Review Settings**.
4. Paste the clipboard into the chat.

It gives the camera's vertical field of view, its pitch, its distance to the ground at y = 0, and a `day` preset: the ambient light facing up and down, the sun's color and intensity, and the sun's direction relative to the camera's heading. Merge them into `rts-art.json`. With `lightUnits` set to `unity`, the render converts Unity's light intensity to Blender's, since Blender's sun lights a surface to 1/π of its strength. HDRP uses physical light units, so there set the intensities by eye against a screenshot of the game.

The renders approximate Unity's look. Post-processing, shadows from neighbors, fog, and tone mapping differ, so check approved buildings in the game too.

## Facing

The export turns each model by `export.turn` degrees about the vertical so its front faces the game camera after import. Which turn that needs depends on the importer's axis conversion and the camera's heading, so the setup checks it once with a test box. If the camera's heading changes later, check again.

## Placing a building

An approved GLB is a model, not a building. Its prefab adds the collider, the footprint or NavMesh obstacle, selection, and any team-color parts, and those stay in Unity. The model's origin is the footprint center on the ground, so a prefab can place it at zero.
