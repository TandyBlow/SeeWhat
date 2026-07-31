"""
Jupyter notebook parsing.
"""
import json


def parse_ipynb(file_path: str) -> str:
    """Parse Jupyter notebook and extract text from all cells."""
    with open(file_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)

    parts: list[str] = []
    for cell in notebook.get('cells', []):
        source = ''.join(cell.get('source', []))
        cell_type = cell.get('cell_type', 'code')

        if cell_type == 'markdown':
            parts.append(source)
        elif cell_type == 'code':
            parts.append(f'```python\n{source}\n```')

    return '\n\n'.join(parts)
