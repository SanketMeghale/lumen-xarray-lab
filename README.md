# lumen-xarray-lab

`lumen-xarray-lab` is a standalone companion repository for building, testing,
and presenting xarray ideas around Lumen without coupling every experiment to
the upstream `lumen` repository.

The separation is deliberate:

- core, mergeable source work belongs upstream in `lumen`
- proposal demos, benchmark harnesses, and experimental helpers live here

## Current Scope

Implemented:

- runnable project scaffold
- lightweight dashboard demo
- example scripts for quickstart, upload flow, and SQL status
- CF-style coordinate detection helpers
- schema enrichment helpers
- benchmark utility functions and scripts
- test suite covering the current lab surface

Still experimental:

- AI upload integration beyond simple previews
- SQL-backed xarray access
- benchmark publication with real datasets and raw result snapshots
- upstream extraction of stable lab features

## Runtime Design

The lab can run in two modes:

1. If a sibling `lumen` checkout with `lumen.sources.xarray.XarraySource`
   exists, the lab uses it.
2. Otherwise, the lab falls back to a local `LabXarraySourceAdapter` that
   implements a compatible subset needed for the demos and tests.

That gives you:

- an isolated repo for demos and proposal artifacts
- a stable fallback when upstream work is still in progress
- a clean migration path from lab code to upstream PRs

## Repository Layout

```text
lumen-xarray-lab/
├─ README.md
├─ LICENSE
├─ pyproject.toml
├─ pixi.toml
├─ .github/workflows/
├─ docs/
├─ src/lumen_xarray_lab/
├─ examples/
├─ benchmarks/
├─ scripts/
├─ tests/
└─ assets/
```

## Quick Start

Install in editable mode:

```bash
pip install -e .[test]
```

Run the example scripts:

```bash
python examples/quickstart.py
python examples/air_temperature_demo.py
python examples/ai_upload_demo.py
python examples/sql_explorer_demo.py
```

Launch the demo dashboard:

```bash
panel serve examples/dashboard_app.py --show
```

Run the tests:

```bash
pytest -q
```

## Build Order

The repository is being built incrementally in this order:

1. top-level packaging, docs, and workflows
2. dataset/runtime layer
3. dashboard internals
4. example scripts and PowerShell helpers
5. benchmark scripts
6. upstream extraction plan

## Useful Entry Points

- [Project metadata](pyproject.toml)
- [Architecture notes](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Benchmark notes](docs/benchmarks.md)
- [Upstream plan](docs/upstream-plan.md)
- [Dashboard app](examples/dashboard_app.py)
- [Source/runtime layer](src/lumen_xarray_lab/datasets.py)
- [Proposal diagram](assets/diagrams/xarray_source_proposal_diagram.svg)

## Proposal Positioning

This repo should support a stronger proposal story than a feature-heavy showcase
package:

- honest implemented-vs-planned boundaries
- working examples and tests for every shipped claim
- clear upstream migration path
- isolated experimentation without polluting core Lumen work
