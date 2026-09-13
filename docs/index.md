# chile-dtpm-gtfs documentation

Version **0.1.0** provides an unofficial Python interface to GTFS publications from
Chile's DTPM, from discovery through a first Metro GeoJSON export. It is independent
of DTPM and does not claim official endorsement.

## Start here

From a checkout, install with `uv sync --locked` (Python 3.12+), then:

```python
from chile_dtpm_gtfs import DTPM

publication = DTPM().current()
with publication.download() as feed:
    metro = feed.metro()
    metro.write_geojson("metro.geojson")
```

For offline work, use `GTFSFeed.from_file("GTFS.zip")`. For a pinned download, use
`GTFSFeed.from_url(url)`. An explicit `destination=` retains a downloaded archive;
otherwise, close the feed or use a context manager to release temporary storage.

## Guides

- [API reference](api.md): public entry points and domain fields.
- [Downloads](downloads.md): streaming, explicit writes, and provenance.
- [GTFS loading](gtfs.md): local/remote sources and basic validation boundaries.
- [Metro selection](metro.md): relationships, hierarchy, shapes, and calendars.
- [GeoJSON](geojson.md): output structure and original geographic coordinates.
- [CLI](cli.md): equivalent command-line workflows.
- [Architecture](architecture.md): responsibilities and dependencies.
- [Testing](testing.md): offline tests, opt-in live checks, and packaging checks.
- [Roadmap](roadmap.md): completed milestone and deferred work.
- [Releasing](releasing.md): local artifacts and explicitly triggered publication.

Source references: [DTPM publication index](https://www.dtpm.cl/index.php/gtfs-vigente),
[GTFS Schedule reference](https://gtfs.org/documentation/schedule/reference/), and
[GeoJSON RFC 7946](https://www.rfc-editor.org/rfc/rfc7946).
