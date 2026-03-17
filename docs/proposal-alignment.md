# Proposal Alignment

This document maps the current prototype to the strongest parts of the GSoC proposal.

## Why This Matters

The prototype should not only look polished. It should reduce mentor uncertainty.

This repo is meant to answer:

- Is the xarray integration technically coherent?
- Is the work already demoable?
- Is there a clear split between prototype proof and upstream-ready implementation?
- Can the project be delivered incrementally instead of as one risky merge?

## Milestone Mapping

| Proposal milestone | Evidence already in the repo | Next upstream move | Why this helps review |
|---|---|---|---|
| Native xarray source boundary | `src/lumen_xarray_lab/datasets.py`, fallback adapter, runtime notes | finalize and isolate upstream `XarraySource` patch in `lumen` | shows the architecture is already narrowed to the right seam |
| Coordinate-aware querying | explorer filters, query preview, pseudo SQL, CF helpers | move stable metadata and coordinate-role behavior upstream | proves this is not just file loading; it is real data interaction |
| Schema and metadata exposure | statistics, dimensions, coordinates, schema tables | keep refining metadata contracts in upstream docs/tests | reassures reviewers that the source integrates with existing Lumen expectations |
| Safe flattening for scientific datasets | benchmark notes, coverage views, `max_rows` framing | land source hardening and guardrails upstream | addresses the highest-risk part of the proposal directly |
| End-to-end user proof | dashboard app, GIF, screenshots, sample datasets | keep as lab-only supporting evidence | makes the proposal concrete and demoable immediately |

## What Is Already Convincing Today

- The explorer already demonstrates dataset loading, filtering, plotting, statistics, coverage, and source-query visibility.
- The README media is generated from the app itself, which avoids the usual demo-repo credibility problem.
- The repo is explicit about experimental areas instead of mixing them into the finished story.
- The architecture, reviewer guide, and upstream plan all point back to an upstream-first contribution model.

## What Still Best Improves Selection Chances

If the goal is to improve GSoC selection odds, these are the highest-value next steps:

1. Prepare the upstream `lumen` xarray patch as a clean, reviewable diff.
2. Keep the lab repo focused on proof, not feature sprawl.
3. Use the lab repo to support the proposal with visuals, benchmarks, and architecture clarity.
4. Document the proposal in terms of incremental PRs instead of a single large merge.

## What Reviewers Should Notice

This repository is intentionally different from a pure showcase package:

- it is designed to support upstream `lumen`
- it separates demo-only work from mergeable work
- it is strict about evidence and scope
- it tries to lower review cost, not just raise feature count

## Suggested Reading Order

1. `README.md`
2. `docs/reviewer-guide.md`
3. `docs/architecture.md`
4. `docs/upstream-plan.md`
5. `src/lumen_xarray_lab/datasets.py`
6. `examples/dashboard_app.py`

## Final Positioning

The strongest version of the proposal is:

- upstream `XarraySource` as the core contribution
- lab repo as proof and demo surface
- tests, docs, and architecture notes as reviewer support

That combination is more convincing than either a proposal-only document or a flashy demo-only repository.
