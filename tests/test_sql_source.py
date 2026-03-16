from __future__ import annotations

import pytest

from lumen_xarray_lab.sql_source import ExperimentalSQLSource


def test_sql_source_status():
    source = ExperimentalSQLSource()
    status = source.status()
    assert status["available"] is False
    assert "experimental" in status["reason"]


def test_sql_source_execute_raises():
    source = ExperimentalSQLSource()
    with pytest.raises(NotImplementedError):
        source.execute("SELECT * FROM air")
