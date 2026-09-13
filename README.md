# chile-dtpm-gtfs

An unofficial Python library for discovering, downloading, loading, and exporting
GTFS data published by Chile's **Directorio de Transporte Público Metropolitano
(DTPM)**. GTFS is the General Transit Feed Specification, a format for transit
schedules and geographic information.

This project specializes in the DTPM distribution for Santiago. It represents the
whole feed, with Metro as the first normalized subset. It is **not affiliated with
or endorsed by DTPM**. The library code is MIT-licensed; that license does not grant
rights to upstream transit data.

## Installation

Python **3.12+** is required. For development from this checkout:

```sh
uv sync --locked
uv run chile-dtpm-gtfs --version
```

To install a locally built v0.1.0 wheel into another environment:

```sh
uv build
uv pip install dist/chile_dtpm_gtfs-0.1.0-py3-none-any.whl
```

A local build does not imply that this version has been published on PyPI.

## Discover the current feed

```python
from chile_dtpm_gtfs import DTPM

dtpm = DTPM()
publications = dtpm.publications()
publication = dtpm.current()
print(publication.title)
print(publication.effective_from)
print(publication.download_url)
```

Discovery reads the [official DTPM index](https://www.dtpm.cl/index.php/gtfs-vigente).
It uses the published ZIP href, never a filename constructed from a date.
`current()` returns metadata without downloading the archive. Future publications
are excluded using today's date in `America/Santiago`; `current(on=date(...))`
allows an explicit applicability date. Equal dates retain page order. Special
service descriptions are preserved without guessing their applicability.

## Download, select Metro, and export GeoJSON

```python
from chile_dtpm_gtfs import DTPM

publication = DTPM().current()
with publication.download() as feed:
    print(feed.metadata.sha256)
    metro = feed.metro()
    metro.write_geojson("metro.geojson")
```

Downloads stream to temporary storage, which the context manager removes. Use
`publication.download(destination="GTFS.zip")` to retain the archive. Existing
archives are not replaced. Network requests support configurable timeouts and
explicit errors; downloads expose SHA-256 and available HTTP size metadata.

## Offline and pinned sources

```python
from chile_dtpm_gtfs import GTFSFeed

with GTFSFeed.from_file("GTFS.zip") as feed:
    print(feed.validate().row_counts)
    metro = feed.metro()

# A normalized snapshot remains usable after closing the feed.
geojson = metro.to_geojson()
metro.write_geojson("metro.geojson", overwrite=True)

# An explicit URL bypasses publication discovery.
with GTFSFeed.from_url("https://example.org/feed.zip") as feed:
    print(feed.metadata)
```

Keep local files unchanged until the feed is closed. Loading validates required
files, headers, and feed_info metadata without reading every large table into
memory. `validate()` fully scans CSV records and service time syntax. This is basic
validation, **not a complete GTFS compliance validator**.

## Normalized data

`metro()` follows routes -> trips -> stop_times -> stops and declared station
hierarchies. It selects standard subway `route_type=1`, never names containing
"Metro". Its immutable snapshot exposes agencies, routes, trips, stops, stop_times,
shapes, and services, plus station/platform/entrance views. All shape variants and
trip directions survive. GTFS times such as `25:10:00` become service seconds.

Use `metro(on=date(...))` for calendar-based service filtering; calendar_dates
exceptions override weekly calendars. Frequency trips remain templates. Generic
`feed.select(route_types=frozenset({...}))` uses the same relational pipeline.
Optional advanced tables remain accessible through `feed.rows("pathways.txt")`
and related table names. Missing optional tables yield no rows.

GeoJSON uses original WGS84 `[longitude, latitude]` coordinates and preserves each
route/shape combination. Missing geometry is null; station hierarchies and lines
are not invented or visually simplified.

## CLI

Prefix with `uv run` when working from this checkout:

```sh
chile-dtpm-gtfs publications
chile-dtpm-gtfs current
chile-dtpm-gtfs download --output GTFS.zip
chile-dtpm-gtfs validate GTFS.zip
chile-dtpm-gtfs export metro --input GTFS.zip --format geojson --output metro.geojson
```

Discovery, download, and validation output JSON. Export prints the written path.
`python -m chile_dtpm_gtfs` also works. See the [CLI guide](docs/cli.md) for options.

## Provenance and limitations

Metadata preserves the requested/resolved URL, source page, advertised effective
date, original filename, UTC download timestamp, byte count, and SHA-256 when
available. Internal feed_start_date/feed_end_date/feed_version remain separate
from publication dates. GeoJSON carries this metadata. Local loading computes a
hash but cannot reconstruct the original download source; retain download metadata
alongside archives when reproducibility matters.

There is no stale-feed fallback or cache. Source layout changes raise explicit
errors and may require a parser update. Missing calendars prevent date filtering
when applicability cannot be determined. Advanced pathways/levels, frequency
expansion, TopoJSON, and runtime JSON are deferred. Selecting large subsets can
require substantial memory even though stop_times input is streamed. The source
and format contracts are documented in the [architecture](docs/architecture.md).

## Documentation and development

- [Documentation home](docs/index.md) and [API reference](docs/api.md)
- [Downloads](docs/downloads.md), [GTFS loading](docs/gtfs.md), [Metro](docs/metro.md),
  and [GeoJSON](docs/geojson.md)
- [Roadmap](docs/roadmap.md), [changelog](CHANGELOG.md), and [release guide](docs/releasing.md)
- [Contributing](CONTRIBUTING.md), [security policy](SECURITY.md), and
  [code of conduct](CODE_OF_CONDUCT.md)

```sh
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m mypy src
uv run --group docs mkdocs build --strict
```

Normal tests use generated ZIPs, HTML fixtures, and mocked HTTP. The live acceptance
test is opt-in; see [testing](docs/testing.md). Code, docstrings, documentation,
and Conventional Commit messages are written in English.
