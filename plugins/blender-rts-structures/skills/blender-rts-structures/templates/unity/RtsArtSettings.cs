// Copies the game camera and daylight into rts-art.json form, so Blender review renders match the game.
// Put this file in an Editor folder, such as Assets/Editor/RtsArtSettings.cs. Open the scene with the
// game camera (tagged MainCamera) and the sun, set the camera as it is in play, then choose
// Tools > RTS Art > Copy Review Settings. The JSON goes to the clipboard and the Console.
using System.Globalization;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class RtsArtSettings
{
    [MenuItem("Tools/RTS Art/Copy Review Settings")]
    static void Copy()
    {
        Camera camera = Camera.main;
        if (camera == null)
        {
            Debug.LogError("RTS Art: tag the game camera MainCamera and try again.");
            return;
        }
        if (camera.orthographic)
        {
            Debug.LogWarning("RTS Art: the game camera is orthographic. Review renders use a perspective camera.");
        }

        Vector3 forward = camera.transform.forward;
        Vector3 heading = new Vector3(forward.x, 0f, forward.z);
        if (heading.sqrMagnitude < 1e-6f)
        {
            Debug.LogError("RTS Art: the camera looks straight down, so it has no heading. Tilt it as in play.");
            return;
        }
        heading.Normalize();
        Vector3 right = new Vector3(heading.z, 0f, -heading.x);
        float pitch = Mathf.Asin(Mathf.Clamp(-forward.y, -1f, 1f)) * Mathf.Rad2Deg;
        // Distance along the view to the ground plane at y = 0.
        float distance = forward.y < -1e-4f ? camera.transform.position.y / -forward.y : 30f;

        Light sun = RenderSettings.sun;
        if (sun == null)
        {
            foreach (Light light in Object.FindObjectsByType<Light>(FindObjectsSortMode.None))
            {
                if (light.type == LightType.Directional && light.isActiveAndEnabled)
                {
                    sun = light;
                    break;
                }
            }
        }
        if (sun == null)
        {
            Debug.LogError("RTS Art: no directional light found. Add the sun, or set it under Lighting > Environment.");
            return;
        }
        RenderPipelineAsset pipeline = GraphicsSettings.currentRenderPipeline;
        if (pipeline != null && pipeline.GetType().Name.Contains("HDRenderPipeline"))
        {
            Debug.LogWarning("RTS Art: HDRP lights use physical units, so set sunIntensity and ambientIntensity by eye.");
        }

        // The ambient light a surface gets facing up and facing down, in linear color.
        Color[] ambient = new Color[2];
        RenderSettings.ambientProbe.Evaluate(new[] { Vector3.up, Vector3.down }, ambient);
        Color sky = ambient[0];
        Color ground = ambient[1];
        float strength = Mathf.Max(sky.maxColorComponent, ground.maxColorComponent);
        if (strength < 1e-3f)
        {
            sky = RenderSettings.ambientSkyColor.linear * RenderSettings.ambientIntensity;
            ground = RenderSettings.ambientGroundColor.linear * RenderSettings.ambientIntensity;
            strength = Mathf.Max(sky.maxColorComponent, ground.maxColorComponent, 1e-3f);
        }

        Vector3 toward = -sun.transform.forward;
        string json =
            "\"camera\": { \"fieldOfView\": " + Number(camera.fieldOfView) +
            ", \"pitch\": " + Number(pitch) +
            ", \"distance\": " + Number(distance) +
            ", \"minDistance\": 8 },\n" +
            "\"day\": {\n" +
            "  \"sky\": \"" + Hex(sky / strength) + "\",\n" +
            "  \"ground\": \"" + Hex(ground / strength) + "\",\n" +
            "  \"ambientIntensity\": " + Number(strength) + ",\n" +
            "  \"sun\": \"#" + ColorUtility.ToHtmlStringRGB(sun.color) + "\",\n" +
            "  \"sunIntensity\": " + Number(sun.intensity) + ",\n" +
            "  \"sunFrom\": { \"right\": " + Number(Vector3.Dot(toward, right)) +
            ", \"up\": " + Number(toward.y) +
            ", \"towardCamera\": " + Number(-Vector3.Dot(toward, heading)) + " },\n" +
            "  \"floor\": \"#4b5a46\"\n" +
            "}";
        EditorGUIUtility.systemCopyBuffer = json;
        Debug.Log("RTS Art: copied review settings for rts-art.json. The camera faces " + Number(heading.x) +
                  ", 0, " + Number(heading.z) + " in world space.\n" + json);
    }

    static string Number(float value)
    {
        return value.ToString("0.###", CultureInfo.InvariantCulture);
    }

    static string Hex(Color linear)
    {
        Color clamped = new Color(Mathf.Clamp01(linear.r), Mathf.Clamp01(linear.g), Mathf.Clamp01(linear.b));
        return "#" + ColorUtility.ToHtmlStringRGB(clamped.gamma);
    }
}
