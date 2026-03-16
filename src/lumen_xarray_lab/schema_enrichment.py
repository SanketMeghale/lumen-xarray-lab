from __future__ import annotations

from copy import deepcopy
from typing import Any


def enrich_schema(
    schema: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    coord_info: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    enriched = deepcopy(schema)
    columns = metadata.get("columns", {}) if metadata else {}

    for name, spec in enriched.items():
        if not isinstance(spec, dict):
            continue
        if name in columns:
            description = columns[name].get("description")
            if description:
                spec["description"] = description
            unit = columns[name].get("unit") or columns[name].get("units")
            if unit:
                spec["unit"] = unit
        if coord_info and name in coord_info:
            role = coord_info[name].get("role")
            if role:
                spec["role"] = role
    return enriched
