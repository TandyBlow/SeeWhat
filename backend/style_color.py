"""
Visual params schema (defaults + required keys), WCAG contrast math,
and the _validate_params sanitizer for AI-generated tree style params.
"""
from typing import Any

# ── Default params (fallback) ──────────────────────────────────────────

DEFAULT_PARAMS: dict[str, Any] = {
    "trunkBaseColor": [0.35, 0.20, 0.10],
    "trunkMidColor": [0.55, 0.35, 0.18],
    "trunkTipColor": [0.35, 0.45, 0.25],
    "leafMidColor": [0.20, 0.60, 0.40],
    "leafLightColor": [0.52, 0.77, 0.32],
    "leafDarkColor": [0.05, 0.36, 0.49],
    "textPrimaryColor": [0.40, 0.50, 1.00],
    "textHintColor": [0.40, 1.00, 0.90],
    "leafShadowSize": -0.25, "leafShadowSoftness": 1.0,
    "leafHighlightSize": -0.25, "leafHighlightSoftness": 1.0,
    "leafAlphaClipping": 0.5, "leafTextureIndex": 0,
    "windStrength": 0.3, "windFrequency": 0.4, "windScale": 0.5,
    "skyTopColor": [0.53, 0.81, 0.92],
    "skyBottomColor": [0.96, 0.94, 0.92],
    "groundColor": [0.36, 0.23, 0.12], "groundUndulation": 0.3,
    "particleColor": [0.4, 0.8, 0.25], "particleShape": 0,
    "particleSpeed": 0.4, "particleDirection": 1,
    "particleSpawnRate": 8, "particleSize": 1.0,
    "mainLightColor": [1.0, 0.95, 0.85], "mainLightIntensity": 2.5,
    "ambientLightColor": [0.6, 0.65, 0.55], "ambientLightIntensity": 0.5,
    "bloomStrength": 0.075, "bloomRadius": 0.4, "bloomThreshold": 0.7,
    "outlineColor": [0.17, 0.10, 0.05], "outlineWidth": 0.3,
    "bgCamY": 2.8, "bgCamPitch": -0.2, "bgCamZ": -5.0, "bgFovZoom": 2.0,
    "bgGroundY": -2.0, "bgHillFreq": 0.3, "bgHillAmp": 5.0,
    "bgHillDepth": 40.0, "bgBldgDepth": 40.0, "bgBuildingDensity": 0.5,
    "bgBuildingHeight": 4.0, "bgFogDistance": 60.0, "bgBarrelK": 0.3,
    "bgPlatformHeight": 0.12, "bgPlatformFade": 0.03, "bgPlatformTexWidth": 1536.0,
}

REQUIRED_COLOR_KEYS = [
    "trunkBaseColor", "trunkMidColor", "trunkTipColor",
    "leafMidColor", "leafLightColor", "leafDarkColor",
    "textPrimaryColor", "textHintColor",
    "skyTopColor", "skyBottomColor", "groundColor",
    "particleColor", "mainLightColor", "ambientLightColor", "outlineColor",
]

REQUIRED_SCALAR_KEYS = [
    "leafShadowSize", "leafShadowSoftness", "leafHighlightSize",
    "leafHighlightSoftness", "leafAlphaClipping", "leafTextureIndex",
    "windStrength", "windFrequency", "windScale",
    "groundUndulation", "particleShape", "particleSpeed",
    "particleDirection", "particleSpawnRate", "particleSize",
    "mainLightIntensity", "ambientLightIntensity",
    "bloomStrength", "bloomRadius", "bloomThreshold",
    "outlineWidth",
    "bgCamY", "bgCamPitch", "bgCamZ", "bgFovZoom",
    "bgGroundY", "bgHillFreq", "bgHillAmp", "bgHillDepth",
    "bgBldgDepth", "bgBuildingDensity", "bgBuildingHeight",
    "bgFogDistance", "bgBarrelK", "bgPlatformHeight",
    "bgPlatformFade", "bgPlatformTexWidth",
]

# WCAG 2.1 minimum contrast ratio for normal text (AA level)
_MIN_CONTRAST_RATIO = 4.5


def _linearize(c: float) -> float:
    """Convert sRGB channel value to linear for luminance calculation."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: list[float]) -> float:
    """WCAG 2.1 relative luminance from sRGB [R,G,B] in 0.0-1.0 range."""
    return 0.2126 * _linearize(rgb[0]) + 0.7152 * _linearize(rgb[1]) + 0.0722 * _linearize(rgb[2])


def _contrast_ratio(lum1: float, lum2: float) -> float:
    """WCAG contrast ratio between two relative luminance values."""
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def _fix_contrast(text_rgb: list[float], bg_lum: float) -> list[float]:
    """Adjust text color to meet minimum contrast against background luminance.

    Tries both lightening and darkening directions and picks the one that
    achieves better contrast while requiring less adjustment.
    """
    text_lum = _relative_luminance(text_rgb)
    if _contrast_ratio(text_lum, bg_lum) >= _MIN_CONTRAST_RATIO:
        return text_rgb  # Already sufficient

    def _search(target: list[float]) -> list[float]:
        lo, hi = 0.0, 1.0
        best = text_rgb
        for _ in range(12):
            mid = (lo + hi) / 2.0
            blended = [
                text_rgb[0] + (target[0] - text_rgb[0]) * mid,
                text_rgb[1] + (target[1] - text_rgb[1]) * mid,
                text_rgb[2] + (target[2] - text_rgb[2]) * mid,
            ]
            if _contrast_ratio(_relative_luminance(blended), bg_lum) >= _MIN_CONTRAST_RATIO:
                best = blended
                hi = mid
            else:
                lo = mid
        return best

    # Try both directions, pick the one with better contrast
    light_result = _search([1.0, 1.0, 1.0])
    dark_result = _search([0.0, 0.0, 0.0])

    light_ratio = _contrast_ratio(_relative_luminance(light_result), bg_lum)
    dark_ratio = _contrast_ratio(_relative_luminance(dark_result), bg_lum)

    winner = light_result if light_ratio >= dark_ratio else dark_result
    return [round(v, 4) for v in winner]


# ── Params validation ─────────────────────────────────────────────────────

def _validate_params(params: dict) -> dict:
    """Validate and fix generated params. Returns cleaned params dict."""
    cleaned = {}
    for key in REQUIRED_COLOR_KEYS:
        val = params.get(key)
        if isinstance(val, list) and len(val) == 3 and all(isinstance(v, (int, float)) for v in val):
            cleaned[key] = [max(0.0, min(1.0, float(v))) for v in val]
        else:
            cleaned[key] = DEFAULT_PARAMS[key][:]

    for key in REQUIRED_SCALAR_KEYS:
        val = params.get(key)
        if isinstance(val, (int, float)):
            cleaned[key] = float(val)
        else:
            cleaned[key] = DEFAULT_PARAMS[key]

    # Ensure text colors have sufficient contrast against background
    sky_lum = (_relative_luminance(cleaned["skyTopColor"]) + _relative_luminance(cleaned["skyBottomColor"])) / 2.0
    cleaned["textPrimaryColor"] = _fix_contrast(cleaned["textPrimaryColor"], sky_lum)
    cleaned["textHintColor"] = _fix_contrast(cleaned["textHintColor"], sky_lum)

    return cleaned
