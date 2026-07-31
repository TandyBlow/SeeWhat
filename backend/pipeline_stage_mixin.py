"""
Pipeline execution stage mixin.

start_pipeline spawns the asyncio.Task and chooses the PDF vs non-PDF runner;
the two background coroutines _run_pdf_pipeline / _run_nonpdf_pipeline buffer
SSE events. Depends on PipelineStateMixin for _write_cache (self._write_cache)
and on the pipeline_state_mixin module-level helpers _PipelineState / _emit /
_elapsed_ms / _make_error_sse.
"""

import asyncio
import logging
import os
import time

from pipeline_state_mixin import (
    _PipelineState, _emit, _elapsed_ms, _make_error_sse,
)

logger = logging.getLogger(__name__)


class PipelineStageMixin:
    """Pipeline stage runner methods (start_pipeline + background coroutines)."""

    async def start_pipeline(
        self,
        file_id: str,
        file_path: str,
        owner_id: str,
        file_ext: str,
        original_filename: str = "",
        max_pages: int = 0,
    ):
        """Launch the pipeline as a background asyncio.Task. Returns immediately."""
        if file_id in self._states:
            logger.warning("Pipeline already registered for %s, skipping", file_id)
            return

        state = _PipelineState(file_id)
        self._states[file_id] = state

        is_pdf = file_path.lower().endswith(".pdf")
        if is_pdf:
            state.task = asyncio.create_task(
                self._run_pdf_pipeline(state, file_path, owner_id, max_pages)
            )
        else:
            state.task = asyncio.create_task(
                self._run_nonpdf_pipeline(state, file_path, owner_id, file_ext)
            )

    # ── internal runners ────────────────────────────────────────────────

    async def _run_pdf_pipeline(
        self, state: _PipelineState, file_path: str, owner_id: str, max_pages: int
    ):
        """Background coroutine: run FullPipeline and buffer SSE events."""
        from pdf_markdown.pipeline import FullPipeline
        from pdf_markdown.streaming import format_sse

        pipe = FullPipeline(file_path, max_pages=max_pages)
        try:
            async for event in pipe.run_streaming():
                sse_str = format_sse(event)
                state.buffered_events.append(sse_str)
                state.new_event.set()
                if event.event == "pipeline_complete":
                    state.final_markdown = event.data.get("final_markdown", "")
                    state.status = "completed"

            if state.final_markdown:
                self._write_cache(owner_id, state.file_id, state.final_markdown)

        except asyncio.CancelledError:
            state.status = "failed"
            state.error_message = "Cancelled by user"
        except Exception as exc:
            logger.error("PDF pipeline failed for %s: %s", state.file_id, exc)
            state.status = "failed"
            state.error_message = str(exc)
            error_sse = _make_error_sse("pipeline", str(exc), False)
            state.buffered_events.append(error_sse)
            state.new_event.set()
        finally:
            state.done.set()
            state.new_event.set()

    async def _run_nonpdf_pipeline(
        self, state: _PipelineState, file_path: str, owner_id: str, file_ext: str
    ):
        """Background coroutine: format non-PDF files and buffer SSE events."""
        from parse_format import format_document_text, should_preserve_verbatim

        try:
            t_start = time.time()
            file_name = os.path.basename(file_path)
            cache_dir = f"/tmp/acacia_uploads/{owner_id}"

            cache_path = os.path.join(cache_dir, f"{state.file_id}.txt")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            else:
                from file_parser import parse_file
                text_content = parse_file(file_path)

            total_chars = len(text_content)

            _emit(state, "pipeline_start", {
                "file_name": file_name,
                "page_count": 0,
                "total_chars": total_chars,
            })

            if not text_content.strip():
                _emit(state, "pipeline_error", {
                    "stage": "extract",
                    "message": "Empty file content",
                    "recoverable": False,
                })
                state.status = "failed"
                state.error_message = "Empty file content"
                return

            if should_preserve_verbatim(file_ext):
                _emit(state, "stage_progress", {
                    "stage": "merge",
                    "detail": "Preserving Markdown source...",
                    "percent": 90,
                    "stageMs": 0,
                    "totalMs": _elapsed_ms(t_start),
                })
                formatted = text_content
            else:
                _emit(state, "stage_progress", {
                    "stage": "annotate",
                    "detail": "Formatting with LLM...",
                    "percent": 30,
                    "stageMs": 0,
                    "totalMs": _elapsed_ms(t_start),
                })
                formatted = await asyncio.to_thread(
                    format_document_text, text_content
                )

            total_ms = _elapsed_ms(t_start)
            _emit(state, "stage_progress", {
                "stage": "merge",
                "detail": "Formatting complete",
                "percent": 90,
                "stageMs": total_ms,
                "totalMs": total_ms,
            })

            _emit(state, "pipeline_complete", {
                "total_markdown_length": len(formatted),
                "issues_found": 0,
                "issues_resolved": 0,
                "unresolved": 0,
                "final_markdown": formatted,
            })

            state.final_markdown = formatted
            state.status = "completed"

            self._write_cache(owner_id, state.file_id, formatted)

        except asyncio.CancelledError:
            state.status = "failed"
            state.error_message = "Cancelled by user"
        except Exception as exc:
            logger.error("Non-PDF pipeline failed for %s: %s", state.file_id, exc)
            state.status = "failed"
            state.error_message = str(exc)
            _emit(state, "pipeline_error", {
                "stage": "annotate",
                "message": str(exc),
                "recoverable": False,
            })
        finally:
            state.done.set()
            state.new_event.set()
