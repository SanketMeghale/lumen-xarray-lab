# Benchmarks

The benchmark layer in this repository is intentionally conservative. It exists
to support engineering decisions, not marketing claims.

## Current Benchmark Scripts

- `benchmarks/flattening_vs_sql.py`
- `benchmarks/netcdf_vs_zarr.py`
- `benchmarks/large_grid_limits.py`

## What They Currently Provide

- flattened row-count estimation from dataset dimensions
- rough DataFrame memory estimates
- a small NetCDF loading timing example
- grid-size scaling intuition for large spatial datasets

## What They Do Not Yet Provide

- production-quality SQL vs native comparisons
- benchmark result publication across many machines
- cloud/object-store performance claims
- broad format coverage with reproducible result archives

## Rules For Publishing Results

Do not turn benchmark output into a public claim unless the result includes:

- dataset description
- hardware and OS details
- exact commands
- raw output
- caveats and unsupported cases

## Intended Next Step

When the SQL prototype becomes real, benchmarks should compare:

- native flattening path
- filtered native path
- SQL-backed query path
- row growth after flattening
- memory safety behavior around `max_rows`
