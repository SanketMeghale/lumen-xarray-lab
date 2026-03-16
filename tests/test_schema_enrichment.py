from __future__ import annotations

from lumen_xarray_lab.schema_enrichment import enrich_schema


def test_enrich_schema():
    schema = {"lat": {"type": "number"}, "temperature": {"type": "number"}}
    metadata = {
        "columns": {
            "lat": {"description": "Latitude"},
            "temperature": {"description": "Air temperature", "units": "degC"},
        }
    }
    coord_info = {"lat": {"role": "latitude"}}
    enriched = enrich_schema(schema, metadata=metadata, coord_info=coord_info)
    assert enriched["lat"]["description"] == "Latitude"
    assert enriched["lat"]["role"] == "latitude"
    assert enriched["temperature"]["unit"] == "degC"
