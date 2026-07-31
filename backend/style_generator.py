"""
AI-powered tree style generator.
Analyzes user knowledge content via DeepSeek and generates
unique TreeStyleParams that visually represent the knowledge landscape.

Pattern follows concept_extractor.py.
"""
from style_cache import (
    _bg_image_cache,
    _cache_key,
    build_profile_text,
    cache_style,
    hydrate_user_state,
)
from style_color import (
    DEFAULT_PARAMS,
    _validate_params,
)
from style_llm import (
    STYLE_SYSTEM_PROMPT,
    _call_deepseek,
    _parse_json,
)
from style_image import _generate_background_image
from style_core import generate_style
