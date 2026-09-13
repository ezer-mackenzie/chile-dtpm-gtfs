"""Select route types by GTFS relationships, retaining all shape variants."""

from collections import defaultdict
from datetime import date
from typing import TYPE_CHECKING

from chile_dtpm_gtfs.domain.models import Shape, ShapePoint, Stop
from chile_dtpm_gtfs.domain.network import TransitNetwork
from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError
from chile_dtpm_gtfs.gtfs import normalize
from chile_dtpm_gtfs.gtfs.calendar import services

if TYPE_CHECKING:
    from chile_dtpm_gtfs.gtfs.feed import GTFSFeed


def _hierarchy(stops: dict[str, Stop], served: set[str]) -> tuple[Stop, ...]:
    selected = set(served)
    stations: set[str] = set()
    for identifier in served:
        visited: set[str] = set()
        current: str | None = identifier
        while current is not None:
            if current not in stops:
                raise InvalidGTFSFeedError(f"Unknown stop or parent station: {current!r}")
            if current in visited:
                raise InvalidGTFSFeedError(f"Cyclic stop hierarchy at {current!r}")
            visited.add(current)
            selected.add(current)
            if stops[current].location_type == 1:
                stations.add(current)
            current = stops[current].parent_station
    # Include entrances, sibling platforms, and their children for these stations.
    children: dict[str, list[str]] = defaultdict(list)
    for item in stops.values():
        if item.parent_station:
            children[item.parent_station].append(item.id)
    pending = list(stations)
    expanded: set[str] = set()
    while pending:
        parent = pending.pop()
        if parent in expanded:
            continue
        expanded.add(parent)
        for child in children[parent]:
            selected.add(child)
            pending.append(child)
    return tuple(stops[key] for key in sorted(selected))


def _shapes(feed: "GTFSFeed", identifiers: set[str]) -> tuple[Shape, ...]:
    points: dict[str, dict[int, ShapePoint]] = defaultdict(dict)
    for row in feed.rows("shapes.txt"):
        identifier = normalize.required(row, "shape_id")
        if identifier not in identifiers:
            continue
        latitude, longitude = normalize.coordinates(row, "shape_pt_lat", "shape_pt_lon")
        if latitude is None or longitude is None:
            raise InvalidGTFSFeedError(f"Missing shape coordinates for {identifier!r}")
        sequence = normalize.integer(
            normalize.required(row, "shape_pt_sequence"), "shape_pt_sequence"
        )
        if sequence in points[identifier]:
            raise InvalidGTFSFeedError(f"Duplicate shape sequence for {identifier!r}")
        distance = row.get("shape_dist_traveled", "")
        points[identifier][sequence] = ShapePoint(
            latitude,
            longitude,
            sequence,
            normalize.number(distance, "shape_dist_traveled") if distance else None,
        )
    if "shapes.txt" in feed.tables:
        missing = identifiers - points.keys()
        if missing:
            raise InvalidGTFSFeedError(f"Referenced shapes are missing: {sorted(missing)}")
    return tuple(
        Shape(key, tuple(points[key][seq] for seq in sorted(points[key]))) for key in sorted(points)
    )


def select_network(
    feed: "GTFSFeed", *, route_types: frozenset[int], on: date | None = None
) -> TransitNetwork:
    """Materialize matching routes via trips and stop times, with optional service-date filtering.

    Only matching stop times and shapes are retained; the large stop_times table
    is scanned once. No timetable or geographic relationships are inferred by name.
    """
    agencies = normalize.unique(normalize.agency(row) for row in feed.rows("agency.txt"))
    all_routes = normalize.unique(normalize.route(row, agencies) for row in feed.rows("routes.txt"))
    routes = {key: item for key, item in all_routes.items() if item.route_type in route_types}
    all_trips = normalize.unique(normalize.trip(row) for row in feed.rows("trips.txt"))
    for item in all_trips.values():
        if item.route_id not in all_routes:
            raise InvalidGTFSFeedError(
                f"Trip {item.id!r} references unknown route {item.route_id!r}"
            )
    trips = {key: item for key, item in all_trips.items() if item.route_id in routes}
    calendars = services(
        {item.service_id for item in trips.values()},
        feed.rows("calendar.txt"),
        feed.rows("calendar_dates.txt"),
    )
    if on is not None:
        active = {item.id for item in calendars if item.is_active(on)}
        trips = {key: item for key, item in trips.items() if item.service_id in active}
    times = []
    sequences: set[tuple[str, int]] = set()
    for row in feed.rows("stop_times.txt"):
        identifier = normalize.required(row, "trip_id")
        if identifier not in all_trips:
            raise InvalidGTFSFeedError(f"Stop time references unknown trip {identifier!r}")
        if identifier not in trips:
            continue
        time = normalize.stop_time(row)
        key = time.trip_id, time.sequence
        if key in sequences:
            raise InvalidGTFSFeedError(f"Duplicate stop sequence: {key!r}")
        sequences.add(key)
        times.append(time)
    stops = normalize.unique(normalize.stop(row) for row in feed.rows("stops.txt"))
    selected_stops = _hierarchy(stops, {item.stop_id for item in times})
    shapes = _shapes(feed, {item.shape_id for item in trips.values() if item.shape_id})
    agency_ids = {item.agency_id for item in routes.values()}
    return TransitNetwork(
        feed.metadata,
        tuple(agencies[key] for key in sorted(agency_ids)),
        tuple(routes[key] for key in sorted(routes)),
        tuple(trips[key] for key in sorted(trips)),
        selected_stops,
        tuple(sorted(times, key=lambda item: (item.trip_id, item.sequence))),
        shapes,
        calendars,
    )
