# Changelog

## Unreleased

No changes yet.

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
