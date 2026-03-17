# Reviewer Guide

This document is meant for a fast technical review of the repository.

## 3-Minute Review Path

If you only have a few minutes, inspect these in order:

1. `README.md`
2. `docs/architecture.md`
3. `docs/upstream-plan.md`
4. `src/lumen_xarray_lab/datasets.py`
5. `examples/dashboard_app.py`

That sequence shows the project story, the architecture boundary, the upstream
plan, the runtime/source layer, and the public demo entry point.

## What Is Already Proven

- xarray-backed datasets can power a Lumen-style explorer surface
- coordinate-aware filtering can happen before flattening
- filtered selections can drive plots, tables, statistics, coverage, and query previews
- schema, metadata, and coordinate roles can be surfaced to the user
- a fallback adapter can keep the lab runnable without blocking on upstream integration
- screenshots and GIFs are generated from the app itself rather than mocked manually

## What Is Upstream-Ready In Spirit

These are the parts that fit the eventual upstream `lumen` story:

- xarray source behavior and query handling
- schema and metadata exposure
- coordinate-role detection and enrichment
- tests and example-driven documentation
- clear limits around flattening and `max_rows`

## What Stays Lab-Only

These are useful for proposal proof, but should not be confused with the
upstream implementation target:

- screenshot and GIF pipelines
- proposal-oriented dashboard shell
- benchmark harnesses
- speculative SQL experiments
- reviewer-facing narrative docs

## Why This Prototype Stands Out

The value of this repo is not feature count alone. The stronger points are:

- **Upstream-first structure:** the repo is designed to feed work back into `lumen`, not become a parallel fork.
- **Runnable proof:** screenshots, GIFs, and examples come from the current app state.
- **Honest scope:** experimental pieces are labeled explicitly instead of presented as finished work.
- **Boundary clarity:** the repo keeps xarray selection upstream of the DataFrame boundary.
- **Reviewability:** architecture notes, benchmark notes, and tests are organized so reviewers can validate claims quickly.

## Suggested Review Questions

These are the right questions to ask when evaluating the prototype:

- Does the xarray-to-DataFrame boundary stay narrow and predictable?
- Are large multidimensional datasets protected from naive flattening?
- Are the UI and screenshots reflecting real current behavior?
- Is the work split cleanly between upstream candidates and demo-only artifacts?
- Do the current tests match the claims being made in the proposal?

## Best Evidence In The Repo

- `docs/architecture.md`
- `docs/benchmarks.md`
- `docs/upstream-plan.md`
- `assets/diagrams/xarray_source_proposal_diagram.svg`
- `assets/screenshots/gallery/`
- `docs/gifs/dashboard_walkthrough.gif`

## Current Non-Goals

This repo does not try to prove:

- full SQL parity
- distributed or large-cluster execution
- replacement of the upstream Lumen explorer
- that every xarray dataset layout is already supported

The current goal is narrower and more useful: prove that upstream xarray support
in Lumen is technically coherent, demoable, and reviewable.
