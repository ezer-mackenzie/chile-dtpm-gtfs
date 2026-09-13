# Domain and Metro selection

```python
from datetime import date
from chile_dtpm_gtfs import GTFSFeed

with GTFSFeed.from_file("GTFS.zip") as feed:
    metro = feed.metro()
    scheduled = feed.metro(on=date(2026, 9, 15))

# The normalized snapshot remains usable after the archive is closed.
for route in metro.routes:
    print(route.id, route.short_name)
```

`metro()` selects standard subway `route_type=1`. It follows routes -> trips ->
stop_times -> stops. Names never determine membership. `select(route_types=...)`
provides the same behavior for an explicit frozenset of GTFS route types. Extended
route types are not automatically classified as Metro in v0.1.0.

`TransitNetwork` exposes immutable tuples of agencies, routes, trips, stops,
stop_times, shapes, and services. Original IDs, route colors, trip directions,
shape IDs, stop parents, location types, platform codes, and level IDs survive
normalization. Times become optional service seconds; shapes keep every original
point in numeric sequence order and every selected variant.

`stations`, `platforms`, and `entrances` derive from declared GTFS hierarchy.
Parent stations, their sibling platforms, entrances, and children are retained.
Unparented boarding stops stay `Stop` objects. The library does not invent parent
stations or group locations by name. A feed without explicit station records can
have a nonempty `stops` collection and an empty `stations` collection.

By default all advertised trips are included. With `on=date(...)`, calendar_dates
exceptions override weekday ranges. Exception-only services are supported. If a
selected service has no calendar information at all, date filtering raises an
explicit error. Route metadata remains present on dates without active trips;
stops and shapes reflect the selected trips. Frequency-based trips are templates,
not expanded departures; inspect frequencies.txt through `feed.rows()`.

Duplicate IDs/sequences, invalid numeric values/coordinates, and broken selected
relationships raise `InvalidGTFSFeedError`. Absent optional shapes are allowed and
trip references are preserved. If a shapes table exists, referenced shapes must
exist. No replacement geometry is invented. This validation covers the normalized
subset, not all advanced GTFS constraints. Advanced pathways, levels, transfers,
and frequencies remain raw accessible tables in this release.

Large stop_times tables are scanned once per selection. Only matching rows are
retained; agencies, routes, trips, and stops are indexed in memory. Repeated calls
perform new scans. Selecting an entire large bus network may need substantially
more memory than selecting Metro.
