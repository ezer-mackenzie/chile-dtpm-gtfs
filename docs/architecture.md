# Architecture

The source layer is implemented as:

```text
DTPM -> DTPMWebsiteClient -> HTML + final URL
                         -> PublicationParser -> FeedPublication[]
                         -> CurrentFeedResolver -> FeedPublication
```

HTTP retrieval, HTML interpretation, and applicability are independent. The public
facade orchestrates them; it contains no scraping or date-selection logic.
The parser fails closed for incomplete advertised blocks. Ties follow page order.

## Dependencies

- httpx: synchronous HTTP, timeouts, redirects, error reporting, and mock transport.
- selectolax: lightweight HTML parsing without browser automation.
- tzdata on Windows: IANA timezone data for America/Santiago.
- pytest, Ruff, mypy: offline tests, formatting/linting, and strict type checking.

Polars, orjson, Typer, and exporters are deferred until their phase needs them.

## Future boundaries and invariants

A downloader will handle streaming ZIP retrieval and provenance independently of
HTML. A GTFS loader will support local files and explicit URLs. Domain models will
separate GTFS parsing from exporters. Metro selection must follow routes -> trips
-> stop_times -> stops, plus parent_station/location_type, never name searches.
Preserve all shape variants and geographic longitude/latitude coordinates. Use
service seconds for GTFS times beyond 24 hours. Calendar exceptions must remain
part of service applicability. Never conflate publication dates with feed_info dates.

The library represents the entire DTPM feed. Metro is its first planned subset.
No GTFS processing, downloader, or empty future module is shipped in phase 1.
