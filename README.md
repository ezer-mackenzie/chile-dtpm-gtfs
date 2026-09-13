# chile-dtpm-gtfs

An unofficial Python library for discovering GTFS publications from Chile's
Directorio de Transporte Público Metropolitano (DTPM). GTFS is the General Transit
Feed Specification, a format for transit schedules and geographic information.
This project specializes in DTPM distribution and is not affiliated with DTPM.

## Status and installation

Phase 1 implements publication discovery only. Downloads, GTFS loading, Metro
selection, GeoJSON, and the CLI are planned and are not available yet.
Python 3.12 or newer is required. The development interpreter is Python 3.14.
Install from this checkout with [uv](https://docs.astral.sh/uv/):

```sh
uv sync
```

## Quick start

```python
from datetime import date
from chile_dtpm_gtfs import DTPM

dtpm = DTPM(timeout=30.0)
publications = dtpm.publications()
publication = dtpm.current()
print(publication.title)
print(publication.effective_from)
print(publication.download_url)

# Resolve against an explicit date for repeatable selection.
publication = dtpm.current(on=date(2026, 9, 1))
```

Each call retrieves the [official publication index](https://www.dtpm.cl/index.php/gtfs-vigente).
Construction makes no request. Discovery never downloads a ZIP. URLs come from
published hrefs; no current archive name is embedded in the library.

## API and behavior

- `DTPM(timeout=30.0, transport=None)`: synchronous discovery facade. A custom
  `httpx.BaseTransport` allows offline testing. HTTP resources close after each call.
- `publications() -> list[FeedPublication]`: entries in page order.
- `current(on=None) -> FeedPublication`: greatest effective date not after `on`.
  The default is today's date in `America/Santiago`. Equal dates use the first
  page entry; this does not infer precedence for election or diversion services.
- `FeedPublication`: immutable `title`, `effective_from`, `download_url`,
  decoded `filename`, and optional `description`. Original wording is retained;
  HTML markup is removed and whitespace normalized.

Advanced offline use separates `PublicationParser().parse(html, source_url=...)`
from `CurrentFeedResolver().resolve(publications, on=...)` in `source.parser` and
`source.resolver`. `source.dates.parse_spanish_date` recognizes Spanish months
without requiring an OS locale. No parser or resolver performs I/O.

Errors in `chile_dtpm_gtfs.exceptions` derive from `DTPMError`:
`DTPMSourceError` wraps HTTP failures, `DTPMSourceParseError` reports malformed or
missing publication blocks, and `NoCurrentPublicationError` reports no applicable
publication. Incomplete blocks and multiple distinct ZIP links fail explicitly.

## Limitations and provenance

The parser supports the observed paragraph/heading followed by ZIP-anchor layout.
A structural website change may require an update. No fallback feed or cache is
used. Descriptions are preserved but special-service applicability is not inferred.
Explicit selection dates do not freeze a changing website: retain HTML snapshots
for repeatable discovery. The URL and publication date identify the advertised
source; download timestamps and SHA-256 provenance will be added with downloads.
Publication dates are separate from future internal GTFS coverage metadata.

## Development

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Tests use synthetic HTML modeled on the official page and mocked HTTP; they never
contact DTPM. See [CONTRIBUTING.md](CONTRIBUTING.md), the
[architecture](docs/architecture.md), and the [phase roadmap](docs/roadmap.md).
