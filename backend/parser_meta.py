"""
Extension-based dispatch and file metadata.
"""
import os
from pathlib import Path

from parser_text import parse_txt, parse_markdown
from parser_pdf import parse_pdf
from parser_docx import parse_docx
from parser_ipynb import parse_ipynb


def parse_file(file_path: str) -> str:
    """
    Parse file based on extension and return text content.

    Args:
        file_path: Path to the file

    Returns:
        Extracted text content

    Raises:
        ValueError: If file type is not supported
        FileNotFoundError: If file does not exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = Path(file_path).suffix.lower()

    parsers = {
        '.txt': parse_txt,
        '.md': parse_markdown,
        '.pdf': parse_pdf,
        '.docx': parse_docx,
        '.ipynb': parse_ipynb,
        '.py': parse_txt,
    }

    parser = parsers.get(file_ext)
    if not parser:
        raise ValueError(f"Unsupported file type: {file_ext}. Supported types: {', '.join(parsers.keys())}")

    return parser(file_path)


def get_file_info(file_path: str) -> dict:
    """Get basic file information."""
    stat = os.stat(file_path)
    return {
        'name': os.path.basename(file_path),
        'size': stat.st_size,
        'extension': Path(file_path).suffix.lower(),
    }
