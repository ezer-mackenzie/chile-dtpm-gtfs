# Normalized JSON export

```python
from chile_dtpm_gtfs import GTFSFeed

with GTFSFeed.from_file("GTFS.zip") as feed:
    network = feed.metro()

document = network.to_json()
network.write_json("metro.json")
```

The exporter serializes the normalized domain snapshot, not raw GTFS CSV rows. Its
versioned top-level document has `schema_version: 1`, `metadata`, and arrays for
`agencies`, `routes`, `trips`, `stops`, `stop_times`, `shapes`, `services`,
`levels`, and `pathways`. Empty collections are arrays, optional values are JSON
`null`, dates use ISO `YYYY-MM-DD`, and stop times are integer seconds from the
service-day start, including values beyond 24 hours.

The `metadata` object carries the feed's source and SHA-256 provenance, using the
same fields as GeoJSON. Service weekdays are booleans in Monday-through-Sunday
order; service exceptions contain their ISO date and `added` flag. Pathways retain
the source direction and attributes. Coordinates remain the original WGS84
latitude/longitude numbers; JSON has no implied coordinate transformation.

Array order follows the normalized snapshot, which is stable for the same feed
and selector. Dictionary field order is stable for a given schema version. New
optional fields may be added in later schema versions; consumers should inspect
`schema_version`. The writer uses atomic UTF-8 output, rejects non-finite numbers,
and never replaces an existing file unless `overwrite=True`.

This format is a domain snapshot, not a GTFS round-trip archive or a promise to
reconstruct source CSV formatting. See [GeoJSON](geojson.md) for geographic
feature output.
