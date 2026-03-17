# lumen-xarray-lab

<p align="center">
  Companion demos, experiments, and proposal assets for bringing xarray into Lumen.
</p>

<p align="center">
  <a href="docs/architecture.md">Architecture</a> &middot;
  <a href="docs/upstream-plan.md">Upstream Plan</a> &middot;
  <a href="examples/dashboard_app.py">Dashboard App</a> &middot;
  <a href="assets/diagrams/xarray_source_proposal_diagram.svg">Proposal Diagram</a>
</p>

## Preview


<table>
  <tr>
    <td width="76%">
      <img src="assets/screenshots/dashboard_desktop.png" alt="Desktop explorer dashboard" />
    </td>
    <td width="24%">
      <img src="assets/screenshots/dashboard_mobile.png" alt="Mobile explorer dashboard" />
    </td>
  </tr>
  <tr>
    <td><strong>Desktop:</strong> overview, dataset summary, explorer controls, and query-aware output.</td>
    <td><strong>Mobile:</strong> the same dashboard rendered in a narrower layout.</td>
  </tr>
</table>

## What This Repo Proves

- xarray-backed datasets can be surfaced through an Explorer-style Lumen workflow.
- Queryable coordinates, schema hints, and preview tables can be generated from real datasets.
- Spatial views, comparison on shared coordinates, and selection-level statistics can be driven from the same explorer.
- The implementation can stay isolated here while stable pieces move upstream into `lumen`.
- The demo story is backed by runnable examples, tests, screenshots, and a walkthrough GIF.

## Current Scope

Implemented:

- explorer-style dashboard with table switching, dimension filters, spatial plots, comparison views, statistics, coverage, export, and query previews
- example scripts for quickstart, upload preview flow, and SQL experiment status
- CF-style coordinate detection helpers
- schema enrichment helpers
- benchmark utility functions and scripts
- test suite covering the current lab surface

Still experimental:

- AI upload integration beyond simple previews
- SQL-backed xarray access
- broader benchmark coverage across larger datasets and machines
- upstream extraction of stable lab features

## Runtime Design

The lab runs in two modes:

1. If a sibling `lumen` checkout exposing `lumen.sources.xarray.XarraySource` exists, the lab uses it.
2. Otherwise, the lab falls back to a local `LabXarraySourceAdapter` that implements the subset required for demos and tests.

That gives you:

- an isolated repo for proposal demos and experiments
- a stable fallback while upstream work is still evolving
- a clean path from lab code to upstream PRs

## Quick Start

Install in editable mode:

```bash
pip install -e .[test]
```

Run the examples:

```bash
python examples/quickstart.py
python examples/air_temperature_demo.py
python examples/ai_upload_demo.py
python examples/sql_explorer_demo.py
```

Launch the dashboard:

```bash
panel serve examples/dashboard_app.py --show
```

Preload a dataset at startup if you want:

```bash
panel serve examples/dashboard_app.py --show --args "C:\path\to\dataset.nc"
```

Inside the dashboard, use the `Load Dataset` card in the sidebar to:

- open a local file path or URI without restarting the server
- load a bundled sample such as `air_temperature`, `rasm`, `ersstv5`, or `compare_weather`
- point the explorer at a local `.zarr` directory
- upload a single NetCDF/HDF file into the current session

Run the tests:

```bash
pytest -q
```

## Media Pipeline

Export the static dashboard snapshot:

```bash
python scripts/make_screenshots.py --html-only
```

Install the demo extras and capture the full media set:

```bash
pip install -e .[demo]
python -m playwright install chromium
python scripts/make_screenshots.py
python scripts/make_gif.py
```

The capture flow now generates:

- `assets/screenshots/dashboard_desktop.png`
- `assets/screenshots/dashboard_mobile.png`
- `docs/screenshots/story_frames/*.png`
- `docs/gifs/dashboard_walkthrough.gif`

## Repository Layout

```text
lumen-xarray-lab/
|- README.md
|- docs/
|- src/lumen_xarray_lab/
|- examples/
|- benchmarks/
|- scripts/
|- tests/
`- assets/
```

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

This repo is meant to support an upstream-friendly proposal story:

- honest implemented-vs-planned boundaries
- working examples and tests for every shipped claim
- clear upstream migration path
- isolated experimentation without polluting core Lumen work
