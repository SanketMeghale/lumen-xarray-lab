from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExperimentalSQLSource:
    reason: str = (
        "SQL-backed xarray access is still experimental in this lab repo and is "
        "not implemented as a stable feature."
    )
    available: bool = False

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "reason": self.reason,
        }

    def execute(self, sql_query: str) -> None:
        raise NotImplementedError(f"{self.reason} Received query: {sql_query}")
