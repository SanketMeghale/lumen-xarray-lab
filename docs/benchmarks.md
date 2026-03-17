# Benchmarks And Limits

This page publishes the current benchmark evidence for the lab repo. The goal
is to prove the shape of the problem, especially row explosion after flattening,
not to make broad performance claims.

## Benchmark Environment

These results were generated on March 17, 2026 on the local proposal machine:

- platform: `Windows-11-10.0.22000-SP0`
- python: `3.13.5`
- logical CPU count: `4`
- memory: `7.88 GB`

## Commands Used

```bash
python benchmarks/flattening_vs_sql.py
python benchmarks/netcdf_vs_zarr.py
python benchmarks/large_grid_limits.py
python benchmarks/multifile_loading.py
python benchmarks/transform_timings.py
```

## Observed Results

| Script | What it measures | Result |
|---|---|---|
| `flattening_vs_sql.py` | Estimated row growth for a medium `time x lat x lon` selection | `3,869,000` flattened rows and about `118.07 MB` for a 4-column DataFrame |
| `netcdf_vs_zarr.py` | Local NetCDF open time for the small air-temperature demo dataset | `0.3703 s` on this machine |
| `large_grid_limits.py` | Estimated row and memory growth for a larger climate-style grid | `378,957,600` rows and about `11.29 GB` for a 4-column DataFrame |
| `multifile_loading.py` | Single-file vs split multi-file open time in the lab adapter | `0.5291 s` for a single file vs `1.4488 s` for a 3-part globbed sample |
| `transform_timings.py` | Transform timings on ERSSTv5 | rolling mean `1.7886 s`, anomaly `0.2499 s`, resample `0.2403 s`, climatology `0.1266 s`, spatial mean `0.0933 s`, zonal mean `0.0785 s` |

## Why These Results Matter

- The medium selection is already large enough to justify filtering before flattening.
- The large-grid estimate shows why `max_rows` is part of the upstream source contract.
- The published NetCDF timing gives a concrete baseline for the small demo dataset.
- The multi-file timing shows that split scientific inputs can be supported in the same explorer workflow while still being explicit about the overhead.
- The ERSSTv5 transform timings show that scientific transforms can be practical enough for interactive prototypes when they stay inside xarray.
- The current environment does not have `zarr` installed, so the Zarr timing remains an explicit gap rather than a fake comparison.

## Known Limitations

- These are single-machine results, not cross-platform benchmarks.
- The DataFrame memory numbers are estimates based on row count and column count, not measured peak memory.
- The NetCDF timing uses a small demo dataset and should not be generalized to large remote stores.
- There is no SQL-vs-native benchmark yet because the SQL path is still experimental.
- There is no Zarr timing yet because the local benchmark environment is missing the `zarr` package.
- The multi-file benchmark uses a split demo dataset, so it measures adapter overhead rather than a large production-scale archive.
- The transform timings are single-run measurements on ERSSTv5 and should be treated as indicative, not as a performance guarantee.

## Raw Reports

- [`benchmarks/results/flattening_vs_sql.json`](../benchmarks/results/flattening_vs_sql.json)
- [`benchmarks/results/netcdf_vs_zarr.json`](../benchmarks/results/netcdf_vs_zarr.json)
- [`benchmarks/results/large_grid_limits.json`](../benchmarks/results/large_grid_limits.json)
- [`benchmarks/results/multifile_loading.json`](../benchmarks/results/multifile_loading.json)
- [`benchmarks/results/transform_timings.json`](../benchmarks/results/transform_timings.json)

## Prototype Takeaway

The benchmark evidence supports the proposal's main implementation choice:

1. resolve the xarray variable first
2. filter in xarray with coordinate-aware selection
3. enforce safety limits like `max_rows`
4. flatten to a DataFrame only after the selection is small enough
