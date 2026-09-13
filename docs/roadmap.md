# Roadmap

The first release milestone is 0.1.0. The package version is not a release claim.
Complete and verify one phase before beginning the next.

1. **Publication discovery (implemented):** package bootstrap, HTTP client,
   immutable metadata, Spanish dates, HTML parser, current resolver, offline tests,
   documentation, and CI.
2. **Downloads and provenance:** explicit download API, HTTP errors, streaming,
   filename/content length, UTC download timestamp, source page, effective date,
   URL, and SHA-256. No implicit downloads in current().
3. **GTFS loading and validation:** from_file/from_url, required agency/stops/routes/
   trips/stop_times files, optional tables, feed_info metadata, invalid ZIP tests,
   and service times beyond 24 hours.
4. **Minimal domain and Metro:** agencies, stops/stations/platforms/entrances,
   routes, trips, shapes, and services; relationship-based selection and all shapes.
5. **GeoJSON:** normalized-domain exporter, in-memory and file APIs, WGS84
   longitude/latitude, fixture-based acceptance tests.
6. **CLI and release readiness:** Typer commands publications/current/download,
   documentation of the complete working pipeline, packaging and release checks.

Each phase must pass pytest, Ruff lint/format, and mypy. Keep changes reviewable
with Conventional Commits. Use Semantic Versioning and v-prefixed Git tags.

Later work: calendar policy improvements, normalized JSON, TopoJSON research,
application runtime datasets, caching, advanced pathways/levels, bus/rail subsets.
KMP applications, APIs, databases, live positions, simulations, and machine learning
are outside the initial library milestone.
