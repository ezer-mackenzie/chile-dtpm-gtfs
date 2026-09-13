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

## Later milestones

- Broader GTFS validation and larger dataset performance measurements.
- Richer publication policy for diversions and special events.
- Frequency expansion, advanced pathways/levels, and station routing.
- More ergonomic bus/rail selectors with documented classification policies.
- Optional cache layers with explicit invalidation and reproducibility controls.
- Normalized JSON, researched TopoJSON support, and application runtime datasets.

KMP applications, web APIs, databases, live positions, simulations, crowdsourcing,
3D models, and machine learning are outside this library's initial scope.

Continue one coherent feature at a time with documentation and meaningful offline
tests. Use Semantic Versioning and v-prefixed release tags; pre-1.0 APIs may evolve
through documented minor releases.
