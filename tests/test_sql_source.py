from __future__ import annotations

import pytest

from lumen_xarray_lab.sql_source import ExperimentalSQLSource


def test_sql_source_status(synthetic_dataset):
    source = ExperimentalSQLSource(dataset=synthetic_dataset)
    status = source.status()
    assert status["available"] is True
    assert status["dialect"] == "sqlite"
    assert "temperature" in status["tables"]


def test_sql_source_execute_select_query(synthetic_dataset):
    source = ExperimentalSQLSource(dataset=synthetic_dataset, max_rows=100)
    result = source.execute('SELECT lat, AVG("temperature") AS mean_temp FROM "temperature" GROUP BY lat ORDER BY lat')

    assert list(result.columns) == ["lat", "mean_temp"]
    assert len(result) == 2


def test_sql_source_execute_rejects_non_select(synthetic_dataset):
    source = ExperimentalSQLSource(dataset=synthetic_dataset)
    with pytest.raises(ValueError):
        source.execute('DELETE FROM "temperature"')
