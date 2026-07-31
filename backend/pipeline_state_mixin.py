"""
State and SSE helpers for pipeline tasks.

Holds the _PipelineState dataclass-like class, the module-level SSE helpers
_emit / _elapsed_ms / _make_error_sse, and PipelineStateMixin with lifecycle
and read methods. PipelineStateMixin must be FIRST in the recomposed class's
MRO so self._states exists before any stage method runs.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class _PipelineState:
    """Per-file pipeline state shared between the background task and SSE readers."""

    def __init__(self, file_id: str):
        self.file_id = file_id
        self.status = "running"
        self.buffered_events: List[str] = []
        self.new_event = asyncio.Event()
        self.done = asyncio.Event()
        self.final_markdown = ""
        self.error_message = ""
        self.task: Optional[asyncio.Task] = None


class PipelineStateMixin:
    """Lifecycle and read methods for pipeline task state."""

    def __init__(self):
        self._states: Dict[str, _PipelineState] = {}

    async def get_events(self, file_id: str):
        """Async generator yielding SSE-formatted strings.

        Replays buffered events first (for late-joining clients), then streams
        new events as they arrive. Terminates when the pipeline signals done.
        """
        state = self._states.get(file_id)
        if state is None:
            return

        position = 0
        while True:
            while position < len(state.buffered_events):
                yield state.buffered_events[position]
                position += 1

            if state.done.is_set():
                return

            state.new_event.clear()
            if position < len(state.buffered_events):
                continue
            await state.new_event.wait()

    async def cancel(self, file_id: str):
        """Cancel a running pipeline task."""
        state = self._states.get(file_id)
        if state is None:
            return
        if state.task and not state.task.done():
            state.task.cancel()
        state.status = "failed"
        state.error_message = "Cancelled by user"
        state.done.set()
        state.new_event.set()

    async def cleanup(self, file_id: str):
        """Remove pipeline state after streaming is complete."""
        self._states.pop(file_id, None)

    def has_task(self, file_id: str) -> bool:
        """Check if a pipeline task is registered in this process."""
        return file_id in self._states

    def get_state(self, file_id: str) -> Optional[Dict]:
        """Return a snapshot of pipeline state for diagnostics."""
        state = self._states.get(file_id)
        if state is None:
            return None
        return {
            "file_id": state.file_id,
            "status": state.status,
            "final_markdown_length": len(state.final_markdown),
            "error": state.error_message,
            "events_buffered": len(state.buffered_events),
        }

    @staticmethod
    def _write_cache(owner_id: str, file_id: str, markdown: str):
        cache_dir = f"/tmp/acacia_uploads/{owner_id}"
        os.makedirs(cache_dir, exist_ok=True)
        fmt_cache_path = os.path.join(cache_dir, f"{file_id}.formatted.txt")
        try:
            with open(fmt_cache_path, "w", encoding="utf-8") as f:
                f.write(markdown)
        except Exception as e:
            logger.warning("Failed to write formatted cache for %s: %s", file_id, e)


# ── helpers ─────────────────────────────────────────────────────────────

def _emit(state: _PipelineState, event: str, data: dict):
    """Format an SSE event string and append to buffer + signal readers."""
    sse_str = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    state.buffered_events.append(sse_str)
    state.new_event.set()


def _elapsed_ms(t_start: float) -> int:
    return int((time.time() - t_start) * 1000)


def _make_error_sse(stage: str, message: str, recoverable: bool = False) -> str:
    data = json.dumps({
        "stage": stage,
        "message": message,
        "recoverable": recoverable,
    }, ensure_ascii=False)
    return f"event: pipeline_error\ndata: {data}\n\n"
