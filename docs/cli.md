# Command-line interface

Install from this checkout with `uv sync`, then prefix commands with `uv run`.
Both `chile-dtpm-gtfs` and `python -m chile_dtpm_gtfs` invoke the same Typer CLI.

```sh
chile-dtpm-gtfs --help
chile-dtpm-gtfs --version
chile-dtpm-gtfs publications
chile-dtpm-gtfs current --on 2026-09-13
chile-dtpm-gtfs download --output GTFS.zip
chile-dtpm-gtfs download --url https://example.org/feed.zip --output pinned.zip
chile-dtpm-gtfs validate GTFS.zip
chile-dtpm-gtfs export metro --input GTFS.zip --format geojson --output metro.geojson
chile-dtpm-gtfs export metro --input GTFS.zip --on 2026-09-15 --output weekday.geojson
```

`publications` and `current` emit publication JSON and fetch only HTML. For current,
`--on` controls publication applicability; without it, today's Santiago date is
used. `download` writes a new archive (default GTFS.zip), checks its structure, and
prints its path and provenance as JSON. Existing archives are not replaced.
`--url` bypasses discovery. Network commands accept `--timeout` in seconds.

`validate` scans all CSV tables and time fields and reports basic validation and
row counts as JSON. It does not claim complete GTFS compliance. File and domain
errors exit with code 1 and an error message on stderr; invalid arguments use
code 2. Successful commands exit with code 0.

`export metro` accepts `--input` for offline use or `--url` for a pinned remote
feed. Without either, it discovers and downloads the official current feed into
temporary storage. `--on` filters service applicability, not publication choice.
Only `--format geojson` is supported. `--overwrite` explicitly permits replacing
an existing output. It prints the written path and releases temporary input data.
The command layer delegates all transport, parsing, selection, and export work
to the same Python APIs used by library consumers.
