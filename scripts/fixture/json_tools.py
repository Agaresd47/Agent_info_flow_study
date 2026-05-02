from __future__ import annotations

import json
import re
from typing import Any, Dict


JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_block(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = JSON_BLOCK_RE.search(stripped)
        if match:
            return json.loads(match.group(0))
        raise
