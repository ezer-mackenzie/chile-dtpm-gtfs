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

`metro()` selects standard subway `route_type=1`; `bus()` selects bus and
trolleybus types `{3, 11}`; `rail()` selects tram, subway, rail, cable tram,
aerial lift, funicular, and monorail types `{0, 1, 2, 5, 6, 7, 12}`. These
convenience methods use only GTFS route_type values, not route or stop names.
`select(route_types=...)` remains available for an explicit frozenset, including
extended route types when the caller knows their meaning.

Each selector follows routes -> trips -> stop_times -> stops. Membership never
depends on names.

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
stops and shapes reflect the selected trips.

Frequency records remain templates by default. Pass `expand_frequencies=True`
to expand rows where `exact_times=1`; generated trip IDs use
`<template-id>@<departure-seconds>`, and the interval is start-inclusive/end-
exclusive with headway-sized steps. Times are shifted relative to the template's
first departure (or arrival when departure is empty). `exact_times=0` or an empty
value remains an unexpanded template because GTFS does not define exact departures
for headway-based service. Expansion is bounded to 100,000 trips and 5,000,000
stop-time records; excess raises `InvalidGTFSFeedError`. Inspect the original
frequency records through `feed.rows("frequencies.txt")`.

Duplicate IDs/sequences, invalid numeric values/coordinates, and broken selected
relationships raise `InvalidGTFSFeedError`. Absent optional shapes are allowed and
trip references are preserved. If a shapes table exists, referenced shapes must
exist. No replacement geometry is invented. This validation covers the normalized
subset, not all advanced GTFS constraints. Advanced pathways, levels, and
frequency expansion are not part of these selectors.

Large stop_times tables are scanned once per selection. Only matching rows are
retained; agencies, routes, trips, and stops are indexed in memory. Repeated calls
perform new scans. Selecting an entire large bus network may need substantially
more memory than selecting Metro.
