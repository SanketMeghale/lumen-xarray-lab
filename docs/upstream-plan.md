# Upstream Plan

The lab is not the final destination for core source functionality. The goal is
to use this repository to clarify, test, and present ideas before moving the
stable parts into upstream `lumen`.

## Priority Upstream Candidates

### 1. Xarray source hardening

- query behavior
- schema and metadata completeness
- docs and examples
- test coverage

### 2. Coordinate-role detection

- better time/lat/lon/vertical inference
- metadata surfaced for filters and views
- predictable behavior on common climate/scientific datasets

### 3. Upload and CLI extension points

- recognizing xarray formats
- loading sources from scientific files cleanly
- exposing the integration through documented extension hooks

## Keep In The Lab

These should remain outside upstream until they are justified:

- proposal-specific dashboards
- benchmark harnesses
- speculative SQL integration
- narrative assets such as screenshots, GIFs, and proposal diagrams

## Proposed PR Sequence

1. source tests and docs
2. metadata/coordinate enrichment
3. extension-point improvements for upload and CLI
4. optional follow-up proposals for more advanced features

## Review Strategy

- keep PRs small
- attach tests with each feature
- avoid bundling demo-only code with core functionality
- prefer honest documentation over broad unverified claims
