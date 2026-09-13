# Architecture

The implementation separates source discovery from feed processing:

```text
DTPMWebsiteClient -> PublicationParser -> FeedPublication[]
                                       -> CurrentFeedResolver
                                       -> FeedPublication
FeedDownloader -> ZIP + DownloadResult -> GTFSLoader -> GTFSFeed
GTFSFeed -> record normalization -> relationship selector -> TransitNetwork
TransitNetwork -> exporter -> GeoJSON dictionary or file
```

`DTPM` orchestrates discovery. `FeedPublication.download()` delegates transport and
loading, then attaches source provenance. `GTFSFeed.from_url()` bypasses discovery;
`from_file()` is fully offline. Parsers do not fetch or cache data. The CLI delegates
to these APIs and contains only argument handling and output presentation.

The ZIP stays on disk. Tables are UTF-8 CSV streams and are never extracted.
Agencies, routes, trips, and stops are indexed during selection; large stop_times
and shapes are scanned while retaining selected records. A normalized snapshot
owns its immutable tuples and survives archive closure. Downloads without a chosen
destination own temporary storage and expose deterministic close/context handling.

## Dependencies

- httpx: HTTP, redirects, timeouts, streaming, and mock transports.
- selectolax: lightweight HTML parsing without browser automation.
- tzdata on Windows: Santiago IANA timezone data.
- Typer: CLI argument handling and help (Rich is transitive).
- pytest, Ruff, mypy: offline tests, formatting/linting, and strict type checks.
- MkDocs in the optional docs group: navigable documentation, not runtime behavior.

Standard-library CSV, ZIP, hashing, and JSON are sufficient for this first Metro
pipeline. Polars may be introduced for measured heavy tabular needs; it does not
shape the public API. There are no empty modules for speculative future features.

## Invariants and limits

Never construct the current archive URL from a date. Preserve published hrefs,
descriptions, and independent publication/internal coverage dates. current() must
not download a ZIP or activate a future publication.

Select Metro through GTFS relationships and retain parent station/location type.
Do not group stops by name or invent missing stations. Preserve every selected
shape variant and original WGS84 points. Store times as service seconds and apply
calendar exceptions before weekly rules. Frequency trips are not expanded in 0.1.0.

Basic validation covers archive structure, CSV streams, integrity and time syntax;
normalization checks supported values and selected relationships. Full standard
validation and advanced station routing remain separate future work. Optional
advanced tables stay available as raw records.

Exporters consume only domain snapshots. GeoJSON includes provenance, all selected
locations, and every route/shape pair. Missing geometry is explicit. No presentation
smoothing is applied. Cache layers, other modes, and other exporters can be added
without changing discovery or coupling exporters to GTFS CSV parsing.
