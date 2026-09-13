# API reference

All public entry points have type annotations and English docstrings. Import
`DTPM`, `FeedPublication`, `GTFSFeed`, and `FeedMetadata` from `chile_dtpm_gtfs`.

## Discovery

| API | Result and behavior |
| --- | --- |
| `DTPM(timeout=30.0, transport=None)` | Construct without I/O; optional httpx transport for testing |
| `dtpm.publications()` | List of advertised publications in page order |
| `dtpm.current(on=None)` | Greatest effective date not after `on` or today in Santiago |
| `publication.download(destination=None, timeout=60.0, max_bytes=2 * 1024**3, transport=None)` | Explicitly download, structurally load, and attach publication provenance |

`FeedPublication` is frozen and has `title`, `effective_from`, `download_url`,
`filename`, optional `description`, and `source_page`. Source words are retained;
whitespace is normalized. Discovery has no cache and no hardcoded current ZIP.

Advanced components: `source.client.DTPMWebsiteClient.fetch()` returns HTML and its
final URL; `source.parser.PublicationParser.parse(html, source_url=...)` reads
metadata; `source.resolver.CurrentFeedResolver.resolve(publications, on=...)`
selects applicability; `source.dates.parse_spanish_date(value)` parses a complete
Spanish date. These parser/resolver operations perform no I/O.

## Downloads and feeds

| API | Result and behavior |
| --- | --- |
| `FeedDownloader(timeout=60.0, max_bytes=2 * 1024**3, transport=None)` | Configurable streaming HTTP layer in `source.downloader` |
| `downloader.download(url, destination, overwrite=False)` | `DownloadResult`; atomic write and SHA-256, without GTFS validation |
| `GTFSFeed.from_file(path)` | Archive-backed feed with structural checks and SHA-256 |
| `GTFSFeed.from_url(url, destination=None, timeout=60.0, max_bytes=2 * 1024**3, transport=None)` | Download and structurally load without scraping |
| `feed.path`, `feed.tables`, `feed.metadata` | Absolute archive path, available table names, immutable metadata |
| `feed.rows("table.txt")` | Streaming string dictionaries; absent optional tables yield no rows |
| `feed.validate()` | `ValidationReport.row_counts` after a full basic CSV/time/integrity scan |
| `feed.metro(on=None)` | Independent normalized snapshot for route type 1 |
| `feed.select(route_types=frozenset({...}), on=None)` | Same pipeline for specified route types |
| `feed.close()` | Remove owned temporary storage; preserve caller-owned files |

Feeds support `with`. A local archive must remain present and unchanged while open.
`from_file()` does not certify full standard compliance. See [GTFS](gtfs.md).

`DownloadResult` fields: `path`, `source_url`, `resolved_url`, `filename`,
`downloaded_at`, `sha256`, `size_bytes`, `content_length`.

`FeedMetadata` fields: `sha256`, `original_filename`, `size_bytes`, `source_url`,
`resolved_url`, `source_page`, `published_effective_from`, `downloaded_at`,
`content_length`, `feed_start_date`, `feed_end_date`, `feed_version`. Source and
coverage fields may be `None`. Datetimes are timezone-aware UTC; dates use `date`.

## Domain snapshots

`domain.network.TransitNetwork` holds tuples of `agencies`, `routes`, `trips`,
`stops`, `stop_times`, `shapes`, and `services`, plus `metadata`. `stations`,
`platforms`, and `entrances` are typed derived views. Records are exported from
`chile_dtpm_gtfs.domain`:

| Model | Fields |
| --- | --- |
| `Agency` | `id`, `name`, `url`, `timezone` |
| `Stop`, `Station`, `Platform`, `Entrance` | `id`, `name`, `latitude`, `longitude`, `location_type`, `parent_station`, `level_id`, `platform_code` |
| `Route` | `id`, `agency_id`, `short_name`, `long_name`, `route_type`, `color`, `text_color` |
| `Trip` | `id`, `route_id`, `service_id`, `direction_id`, `shape_id`, `headsign` |
| `StopTime` | `trip_id`, `stop_id`, `sequence`, `arrival_seconds`, `departure_seconds` |
| `Shape` | `id`, ordered `points` |
| `ShapePoint` | `latitude`, `longitude`, `sequence`, optional `distance_traveled` |
| `Service` | `id`, `start_date`, `end_date`, `weekdays`, `exceptions`; method `is_active(on)` |
| `ServiceException` | `on`, `added` |

`Service.is_active()` applies exceptions first and raises when no calendar data is
available. `gtfs.time.parse_service_time(value)` returns integer service seconds
and accepts hours beyond 24. Blank intermediate values become `None` in StopTime.

## Export and errors

`network.to_geojson()` returns a JSON-compatible dictionary.
`network.write_geojson(path, overwrite=False)` atomically writes it and returns a
Path. `exporters.geojson.GeoJSONExporter` implements the small
`exporters.base.Exporter` protocol. Export requires no open feed or HTTP access.

Errors in `chile_dtpm_gtfs.exceptions` derive from `DTPMError`:

| Error | Meaning |
| --- | --- |
| `DTPMSourceError` | HTTP publication retrieval failed |
| `DTPMSourceParseError` | Advertised metadata is missing, invalid, or ambiguous |
| `NoCurrentPublicationError` | No publication applies on the requested date |
| `FeedDownloadError` | Download or destination write failed |
| `InvalidGTFSFeedError` | Archive, supported records, or selected relationships are invalid |
| `FeedExportError` | Output cannot be represented or written |

Invalid configuration such as a nonpositive download limit raises `ValueError`.
