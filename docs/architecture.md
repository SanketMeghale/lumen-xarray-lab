# Architecture

This repository is intentionally split into two layers:

1. `lumen` upstream work
2. lab-only demo and experiment work

The lab should never become a shadow fork of Lumen. It exists to make proposal
work, demos, and experiments easier to iterate on while keeping the upstream
integration path clear.

## Runtime Flow

```text
xarray dataset or URI
  -> lumen_xarray_lab.datasets.build_source()
  -> prefer sibling lumen.sources.xarray.XarraySource
  -> otherwise use LabXarraySourceAdapter
  -> enrich schema and coordinate metadata
  -> dashboard, examples, and benchmarks consume the result
```

## Layer Responsibilities

### Upstream layer

These belong in `lumen` once they are stable:

- `XarraySource` behavior and API hardening
- coordinate-aware metadata and schema improvements
- docs and example specs that fit Lumen conventions
- upload/CLI extension points

### Lab layer

These stay here until they are proven or intentionally remain demo-only:

- proposal dashboards
- benchmark harnesses
- incomplete SQL experiments
- side-by-side workflow comparisons

## Why The Fallback Adapter Exists

The lab must stay runnable even when:

- the upstream xarray work is not installed
- the local Lumen branch is in flux
- reviewers want to try the repo without patching another checkout first

The fallback adapter is intentionally narrow. It only implements the subset of
behavior needed by the current demos and tests.

## Current Package Boundaries

- `datasets.py`: source resolution, fallback adapter, demo dataset handling
- `cf.py`: coordinate-role detection and metadata extraction
- `schema_enrichment.py`: merges schema with metadata and coordinate roles
- `dashboard/`: proposal-oriented UI shell
- `ai_hooks.py`: path detection and lightweight upload/CLI helpers
- `sql_source.py`: explicit placeholder for future SQL experiments

## Review Principle

Any feature that graduates from the lab should satisfy all of the following:

- clear value to Lumen users
- tests
- honest scope boundaries
- incremental upstream PR shape
