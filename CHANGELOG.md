# Changelog

## Unreleased

No changes yet.

## 1.0.0 - 2026-10-23

First stable API milestone. The version is tagged as `v1.0.0`; GitHub release and
PyPI publication are separate actions and are not implied by this tag.

### Added

- Deterministic DTPM applicability, core validation diagnostics, bus/rail
  selectors, opt-in exact-time frequency expansion, and normalized pathways/levels.
- Versioned normalized JSON export alongside provenance-preserving GeoJSON.
- Documented API compatibility policy, generated-feed benchmarks, and the release
  acceptance gates for supported Python environments.

## 0.9.0 - 2026-10-23

### Changed

- Reviewed documented imports and made `TransitNetwork` an explicit domain export;
  clarified that implementation modules are not API compatibility boundaries.

## 0.8.0 - 2026-10-23

### Changed

- Expanded the synthetic benchmark to measure loading, validation, selection, and
  both exporters; documented reproducible, threshold-free performance checks.
- Kept implementation streaming and avoided speculative optimizations because
  generated-feed measurements did not identify an actionable bottleneck.

## 0.7.0 - 2026-10-23

### Added

- Versioned normalized JSON serialization for all selected domain records, with
  provenance and atomic file output through the Python API and CLI.

## 0.6.0 - 2026-10-23

### Added

- Immutable `Level` and `Pathway` domain records on selected transit networks,
  preserving only source-declared connectivity with endpoints in the selection.

## 0.5.0 - 2026-10-23

### Added

- Opt-in exact-time frequency expansion with deterministic generated IDs, preserved
  headway templates, and bounded generated trip/stop-time counts.

## 0.4.0 - 2026-10-23

### Added

- `GTFSFeed.bus()` and `GTFSFeed.rail()` convenience selectors using standard
  GTFS route types and the existing relationship-based pipeline.

## 0.3.0 - 2026-10-23

### Changed

- Clarified publication applicability: only the source's explicit effective date
  is used, future entries are excluded, and equal dates retain page order.
- Special-service and diversion descriptions remain informational and are never
  converted into inferred applicability windows.

## 0.2.0 - 2026-10-23

### Added

- Core GTFS validation diagnostics for common field, identifier, calendar, time,
  coordinate, and relationship errors, while retaining structural exceptions.
- Validation report status and bounded diagnostics in the Python API and CLI.

## 0.1.0 - 2026-09-13

Initial release milestone (publication is a separate action).

### Added

- Official DTPM publication discovery using real hrefs and locale-independent
  Spanish dates, with Santiago-aware current applicability and explicit errors.
- Streaming downloads with atomic destination writes, size checks, SHA-256,
  requested/resolved URLs, original filenames, and UTC download provenance.
- Local and explicit-URL GTFS loading, required/optional tables, basic CSV/integrity
  validation, independent feed_info metadata, and service times beyond 24 hours.
- Immutable transit models and relationship-based Metro selection with declared
  station hierarchy, all shape variants, and calendar exception handling.
- In-memory and file GeoJSON export preserving WGS84 positions and provenance.
- Typer CLI for publications, current, download, validate, and export metro.
- Offline fixtures, opt-in live acceptance testing, compatibility checks, CI,
  packaging checks, MkDocs documentation, and release configuration.

### Limitations

Validation is intentionally basic. Advanced pathways/levels, frequency expansion,
TopoJSON, caching, and runtime JSON are deferred. This is unofficial DTPM software.
