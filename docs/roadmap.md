# Roadmap

This roadmap is ordered to support a proposal and an upstream contribution path
at the same time.

## Phase 1: Foundation

- finalize repo structure
- keep examples runnable
- make the fallback runtime adapter predictable
- document the boundaries between lab and upstream code

Exit criteria:

- examples run
- tests pass
- docs explain what is real vs experimental

## Phase 2: Presentation

- strengthen dashboard presentation
- add screenshots and a short demo capture
- improve architecture and benchmark documentation

Exit criteria:

- mentors can understand the project from the repo alone
- one clean dashboard demo is available

## Phase 3: Coordinate Intelligence

- improve coordinate detection heuristics
- surface richer coordinate metadata in schema and UI
- test more naming and attribute conventions

Exit criteria:

- common time/lat/lon patterns auto-detect correctly
- metadata is visible in the lab UI and docs

## Phase 4: AI And CLI Extensions

- improve upload helpers
- document CLI integration patterns
- prototype ingestion hooks that could move upstream later

Exit criteria:

- upload flow is demonstrated clearly
- extension-point needs are documented for upstream review

## Phase 5: SQL Experimentation

- keep SQL work explicitly experimental
- compare benefits and costs against native flattening
- publish benchmark results only with raw evidence

Exit criteria:

- benchmark scripts are reproducible
- README claims remain conservative

## Phase 6: Upstream Extraction

- split proven features into focused upstream PRs
- remove any unnecessary duplication between the lab and Lumen
- keep the lab as a demo/benchmark repo, not a fork
