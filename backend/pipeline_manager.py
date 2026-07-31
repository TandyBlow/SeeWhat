"""
Recomposed PipelineTaskManager from the state and stage mixins.

PipelineStateMixin comes first in the MRO so its __init__ runs and self._states
is initialized before start_pipeline is ever called.
"""

import logging

from pipeline_state_mixin import PipelineStateMixin
from pipeline_stage_mixin import PipelineStageMixin

logger = logging.getLogger(__name__)


class PipelineTaskManager(PipelineStateMixin, PipelineStageMixin):
    """Manages lifecycle of background pipeline tasks.

    Module-level singleton: _pipeline_manager.
    Uses asyncio.Event for signaling — supports multiple concurrent SSE readers
    and late-joining clients that receive a full event replay from the buffer.
    """


# ── module-level singleton ──────────────────────────────────────────────

_pipeline_manager = PipelineTaskManager()
