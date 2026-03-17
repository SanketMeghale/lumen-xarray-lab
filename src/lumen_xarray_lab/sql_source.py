from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any

import pandas as pd
import xarray as xr

from .datasets import make_dataframe_panel_safe, sample_table_dataframe


@dataclass
class ExperimentalSQLSource:
    dataset: xr.Dataset | None = None
    filterable_coords: list[str] | None = None
    max_rows: int = 5000
    dialect: str = "sqlite"
    reason: str = (
        "Lightweight SQL explorer over bounded DataFrame previews. "
        "It is intended for reviewer-friendly inspection, not as a production SQL backend."
    )
    available: bool = True

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "dialect": self.dialect,
            "max_rows": self.max_rows,
            "reason": self.reason,
            "tables": self.list_tables(),
        }

    def list_tables(self) -> list[str]:
        if self.dataset is None:
            return []
        return list(self.dataset.data_vars)

    def example_queries(self, preferred_table: str | None = None) -> list[str]:
        tables = self.list_tables()
        if not tables:
            return ["SELECT 1 AS empty_result"]

        table = preferred_table if preferred_table in tables else tables[0]
        arr = self.dataset[table]
        dims = [dim for dim in arr.dims if dim in arr.coords]
        value_col = table
        examples = [
            f'SELECT * FROM "{table}" LIMIT 12',
            f'SELECT COUNT(*) AS row_count, MIN("{value_col}") AS min_value, MAX("{value_col}") AS max_value FROM "{table}"',
        ]

        if dims:
            first_dim = dims[0]
            examples.append(
                f'SELECT "{first_dim}", AVG("{value_col}") AS mean_value FROM "{table}" '
                f'GROUP BY "{first_dim}" ORDER BY "{first_dim}" LIMIT 24'
            )
        if len(dims) >= 2:
            second_dim = dims[1]
            examples.append(
                f'SELECT "{dims[0]}", "{second_dim}", "{value_col}" FROM "{table}" '
                f'ORDER BY "{dims[0]}", "{second_dim}" LIMIT 24'
            )
        return examples

    def _load_table_frame(self, table: str) -> pd.DataFrame:
        if self.dataset is None:
            raise ValueError("An xarray dataset is required for SQL exploration.")
        return make_dataframe_panel_safe(
            sample_table_dataframe(
                self.dataset,
                table,
                limit=self.max_rows,
                filterable_coords=self.filterable_coords,
            )
        )

    def execute(self, sql_query: str) -> pd.DataFrame:
        if self.dataset is None:
            raise ValueError("An xarray dataset is required for SQL exploration.")

        query = sql_query.strip()
        if not query:
            raise ValueError("Provide a SQL query to execute.")

        lowered = query.lower()
        if not lowered.startswith(("select", "with")):
            raise ValueError("Only SELECT and WITH queries are supported in the lightweight SQL explorer.")

        connection = sqlite3.connect(":memory:")
        try:
            for table in self.list_tables():
                frame = self._load_table_frame(table)
                frame.to_sql(table, connection, index=False, if_exists="replace")
            result = pd.read_sql_query(query, connection)
        finally:
            connection.close()

        result = make_dataframe_panel_safe(result)
        if len(result) > self.max_rows:
            result = result.head(self.max_rows)
        return result
