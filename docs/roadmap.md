# Roadmap

## v0.1.0: completed initial milestone

1. Publication discovery: official HTTP index, immutable metadata, Spanish dates,
   actual ZIP hrefs, current resolver, source exceptions, and offline HTML tests.
2. Downloads: streaming, explicit destination behavior, HTTP errors, byte limits,
   timestamps, source/resolved URLs, original filename, Content-Length, and SHA-256.
3. GTFS: local/URL entry points, archive/header checks, streaming required/optional
   tables, independent feed_info metadata, service times, and basic validation.
4. Domain and Metro: typed immutable records, relationship-based selection,
   station hierarchy, all shapes, and calendar exception-aware service filtering.
5. GeoJSON: normalized-domain exporter, in-memory/file APIs, WGS84 coordinates,
   route variants, provenance, and atomic output.
6. CLI and release preparation: discovery/current/download/validate/export commands,
   Python compatibility checks, packaging, CI, documentation, and release workflow.

Changes were implemented and verified in separate Conventional Commits. A local
milestone/tag does not imply that a GitHub release or PyPI upload has occurred.

## Proposed path to v1.0.0

These are ordered milestones, not a promise to implement every GTFS feature. Each
phase should remain a separate, documented change with offline tests. Re-evaluate
scope at phase boundaries; defer work that does not improve the library's core
publication-to-domain workflow.

### v0.2.0: actionable GTFS validation (implemented; release pending)

- Extend validation beyond CSV structure and service-time syntax with useful,
  record-specific diagnostics for core GTFS fields and relationships.
- Keep validation separate from loading and normalization. Do not describe it as
  complete GTFS certification unless the implemented rules justify that claim.
- Add scalable generated-feed tests and reproducible performance measurements.
  Avoid brittle wall-clock limits in cross-platform CI; investigate regressions
  against the same fixture and environment.

### v0.3.0: publication applicability policy (implemented; release pending)

- Support DTPM special-service or diversion applicability only when the source
  provides enough information for a deterministic result.
- Preserve source descriptions and page order; never infer applicability from
  ambiguous text or silently substitute a stale publication.
- Cover normal, special, ambiguous, and future publication cases with local HTML
  fixtures and Santiago-date tests.

### v0.4.0: documented mode selectors (implemented; release pending)

- Add convenient bus and rail selectors using standard GTFS `route_type` values
  and the existing relationship-based selection pipeline.
- Make classification boundaries explicit; do not classify modes by route or stop
  names, and keep the generic `select(route_types=...)` API available.

### v0.5.0: opt-in frequency expansion

- Add frequency-based trip expansion only behind an explicit API choice.
- Define exact-time and headway behavior, date/calendar interaction, generated
  identifiers, and limits before implementation.
- Preserve the current template representation and existing selector behavior by
  default; test boundary and extended-service times offline.

### v0.6.0: station pathways and levels

- Normalize GTFS pathways and levels sufficiently to expose declared station
  connectivity and accessibility attributes.
- Keep graph traversal separate from Metro selection and avoid inventing links,
  transfer times, or accessibility guarantees absent from source data.

### v0.7.0: normalized JSON export

- Export the normalized domain model, not raw GTFS CSV rows.
- Document a deterministic output shape, metadata/provenance treatment, and
  behavior for optional values; test round-trip JSON encoding and file writes.

### v0.8.0: performance and usability hardening

- Measure representative load, validation, selection, and export workflows on
  generated fixtures sized to expose memory or runtime problems.
- Optimize only measured bottlenecks, preserve streaming/resource ownership, and
  publish practical limits and examples in the user guides.

### v0.9.0: release candidate and API review

- Review every public symbol, error, selector, report, and exporter for coherent
  naming, type annotations, lifecycle behavior, and documentation.
- Resolve known correctness issues, document deliberate limitations, verify the
  supported Python/OS matrix, and run the full release checks before declaring an
  API candidate stable.
- Record incompatible pre-1.0 changes and migration guidance; do not hide them in
  a release-preparation commit.

## v1.0.0 acceptance criteria

The release is ready when all of the following hold:

1. The documented DTPM discovery, download, local/explicit-URL GTFS loading,
   provenance, core normalization, Metro and mode selection, calendar handling,
   and GeoJSON/JSON export workflows work end to end.
2. Validation has a documented, tested scope and actionable diagnostics; any
   unsupported GTFS rules are clearly identified rather than implied to be checked.
3. Publication applicability is deterministic, source descriptions and actual
   links are retained, and unknown or future entries are never silently activated.
4. Public APIs remain typed and documented; downloads/feed resources have explicit
   ownership and errors; documented output preserves source coordinates and
   provenance.
5. Offline tests pass on supported Python versions and operating systems, live
   tests remain opt-in, and coverage remains at or above the configured 90% gate.
6. Ruff lint/format, strict mypy, strict MkDocs, wheel/sdist builds, and the
   installed-distribution check all pass. Installation is tested outside the
   checkout and distribution contents exclude real feeds and test fixtures.
7. README, API guides, changelog, package version, and release instructions agree
   on the shipped behavior and version. A v1.0.0 tag or publication happens only
   after explicit approval.

These quality gates carry forward the reference library's emphasis on typed
public APIs, strict static checking, multi-version testing, and user documentation.
The implementation remains tailored to this package: synchronous HTTP, immutable
domain snapshots, explicit provenance, and no unnecessary schema framework or
runtime dependency.

## Deferred beyond v1.0.0

Caching, TopoJSON, application runtime datasets, KMP applications, web APIs,
databases, live positions, simulations, crowdsourcing, 3D models, and machine
learning are not prerequisites for a stable core library. Revisit them only with a
specific user need and a separately reviewed design.

Use Semantic Versioning and v-prefixed release tags. Before 1.0, APIs may evolve
through documented minor releases; v1.0.0 marks the start of a stability promise
for the documented public API.
