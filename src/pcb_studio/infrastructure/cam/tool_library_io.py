"""Strict versioned JSON exchange for nominal tool libraries."""
import json
from dataclasses import asdict
from pathlib import Path

from pcb_studio.domain.tools import CuttingTool, ToolLibrary


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_tool_library(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if (not isinstance(data, dict) or set(data) != {"schema_version", "tools"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or not isinstance(data["tools"], list)):
        raise ValueError("Unsupported tool library schema")
    try:
        return ToolLibrary(tuple(CuttingTool(**row) for row in data["tools"]))
    except TypeError as exc:
        raise ValueError("Invalid tool record fields") from exc


def tool_library_json(library: ToolLibrary):
    return json.dumps({"schema_version": 1, "tools": [asdict(t) for t in library.tools]},
                      indent=2, allow_nan=False) + "\n"
