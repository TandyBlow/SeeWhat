"""
Background parse task registry and daemon-thread runners.

Shared module-level state _parse_tasks (dict) and _lock live here;
enqueue_parse / get_parse_progress / _run_parse_thread mutate them under the
lock. _run_format_thread is spawned as a separate daemon thread and calls
format_document_text / should_preserve_verbatim from parse_format.py.
"""

import logging
import os
import threading

from parse_format import format_document_text, should_preserve_verbatim

logger = logging.getLogger(__name__)

_parse_tasks: dict[str, dict] = {}
_lock = threading.Lock()


def _run_format_thread(owner_id: str, file_id: str, file_ext: str) -> None:
    """Background thread: read cached text, format it, write .formatted.txt."""
    try:
        cache_dir = f"/tmp/acacia_uploads/{owner_id}"
        txt_path = os.path.join(cache_dir, f"{file_id}.txt")
        fmt_path = os.path.join(cache_dir, f"{file_id}.formatted.txt")

        if not os.path.exists(txt_path):
            return

        with open(txt_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

        if not text_content.strip():
            return

        # Check for extracted images
        img_dir = os.path.join("/tmp/acacia_uploads/images", file_id)
        image_urls: list[str] = []
        if os.path.exists(img_dir):
            image_urls = sorted(
                f"/file-images/{file_id}/{f}"
                for f in os.listdir(img_dir)
            )

        if should_preserve_verbatim(file_ext):
            formatted = text_content
        else:
            formatted = format_document_text(text_content, image_urls)

        with open(fmt_path, 'w', encoding='utf-8') as f:
            f.write(formatted)

        logger.info(f"Background formatting complete for {file_id}: {len(formatted)} chars")

    except Exception as e:
        logger.warning(f"Background formatting failed for {file_id}: {e}")


def enqueue_parse(file_id: str, file_path: str, owner_id: str, file_ext: str,
                  original_filename: str = "") -> None:
    """Start background file parsing. Non-blocking — returns immediately."""
    with _lock:
        _parse_tasks[file_id] = {
            "status": "processing",
            "stage": "parsing",
            "error": "",
            "filename": original_filename,
        }

    thread = threading.Thread(
        target=_run_parse_thread,
        args=(file_id, file_path, owner_id, file_ext),
        daemon=True,
    )
    thread.start()
    logger.info(f"Enqueued background parse for {file_id} ({file_ext}) orig_name={original_filename}")


def get_parse_progress(file_id: str) -> dict | None:
    """Return parse progress dict or None if no task is registered."""
    with _lock:
        return _parse_tasks.get(file_id)


def _run_parse_thread(file_id: str, file_path: str, owner_id: str, file_ext: str) -> None:
    """Background thread: parse file, check OCR for PDFs, write cache."""
    from file_parser import parse_file, get_file_info

    # Read original filename from task state
    with _lock:
        task = _parse_tasks.get(file_id, {})
        original_filename = task.get("filename", "")

    try:
        # Stage 1: parse file
        with _lock:
            if file_id in _parse_tasks:
                _parse_tasks[file_id]["stage"] = "parsing"

        text_content = parse_file(file_path)
        file_info = get_file_info(file_path)

        ocr_status = "not_needed"
        need_ocr_reason = ""
        total_pages = 0

        # Stage 2: OCR check for PDFs
        if file_ext == ".pdf":
            with _lock:
                if file_id in _parse_tasks:
                    _parse_tasks[file_id]["stage"] = "ocr_check"

            from pdf_ocr import needs_ocr, get_page_count

            need_ocr_reason = needs_ocr(file_path)

            if need_ocr_reason:
                from ocr_task_manager import enqueue_ocr

                total_pages = get_page_count(file_path)
                is_garbled = need_ocr_reason == "text_garbled"
                enqueue_ocr(
                    file_id, file_path, owner_id,
                    total_pages=total_pages,
                    is_garbled=is_garbled,
                )
                ocr_status = "pending"
                logger.info(
                    f"Enqueued background OCR for {file_id} "
                    f"(reason={need_ocr_reason}, pages={total_pages})"
                )

        # Write cache
        cache_dir = os.path.dirname(file_path)
        cache_path = os.path.join(cache_dir, f"{file_id}.txt")
        with open(cache_path, "w", encoding="utf-8") as cf:
            cf.write(text_content)

        # Stage 3: ready
        with _lock:
            _parse_tasks[file_id] = {
                "status": "ready",
                "stage": "ready",
                "error": "",
                "result": {
                    "file_id": file_id,
                    "filename": original_filename or os.path.basename(file_path),
                    "size": file_info["size"],
                    "extension": file_info["extension"],
                    "text_length": len(text_content),
                    "text_preview": text_content[:200] + "..." if len(text_content) > 200 else text_content,
                    "ocr_applied": False,
                    "ocr_reason": need_ocr_reason or None,
                    "ocr_status": ocr_status,
                    "total_pages": total_pages,
                },
            }

        logger.info(f"Parse complete for {file_id}: {len(text_content)} chars, ocr={ocr_status}")

        # Spawn async formatting — file is already "ready", this is a bonus
        fmt_thread = threading.Thread(
            target=_run_format_thread,
            args=(owner_id, file_id, file_ext),
            daemon=True,
        )
        fmt_thread.start()

    except Exception as e:
        logger.error(f"Parse failed for {file_id}: {e}")
        # Clean up file on error
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e2:
                logger.warning("Failed to clean up temp file %s after parse failure: %s", file_path, e2)
        with _lock:
            _parse_tasks[file_id] = {
                "status": "failed",
                "stage": "failed",
                "error": str(e),
            }
