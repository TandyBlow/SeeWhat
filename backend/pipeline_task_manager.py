"""
Background pipeline task manager for file extraction.

Decouples pipeline execution from the SSE request handler:
- Pipeline starts immediately after upload (POST /upload-file)
- SSE endpoint (GET /extract-stream) reads from a buffered event stream
- Supports multiple concurrent SSE readers and late-joining clients
"""

from pipeline_manager import _pipeline_manager
