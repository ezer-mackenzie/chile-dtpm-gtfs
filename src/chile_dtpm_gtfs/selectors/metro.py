"""Select route types by GTFS relationships, retaining all shape variants."""

from collections import defaultdict
from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING

from chile_dtpm_gtfs.domain.models import Shape, ShapePoint, Stop, StopTime, Trip
from chile_dtpm_gtfs.domain.network import TransitNetwork
from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError
from chile_dtpm_gtfs.gtfs import normalize
from chile_dtpm_gtfs.gtfs.calendar import services
from chile_dtpm_gtfs.gtfs.time import parse_service_time

if TYPE_CHECKING:
    from chile_dtpm_gtfs.gtfs.feed import GTFSFeed

MAX_EXPANDED_TRIPS = 100_000
MAX_EXPANDED_STOP_TIMES = 5_000_000


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


def _expand_frequencies(
    trips: dict[str, Trip],
    stop_times: list[StopTime],
    frequency_rows: list[dict[str, str]],
) -> tuple[dict[str, Trip], list[StopTime]]:
    """Expand exact-time frequency windows; retain headway-only templates."""
    windows: dict[str, list[tuple[int, int, int, bool]]] = defaultdict(list)
    for row in frequency_rows:
        identifier = normalize.required(row, "trip_id")
        if identifier not in trips:
            continue
        try:
            start = parse_service_time(normalize.required(row, "start_time"))
            end = parse_service_time(normalize.required(row, "end_time"))
        except InvalidGTFSFeedError as exc:
            raise InvalidGTFSFeedError(
                f"Invalid frequency window for trip {identifier!r}: {exc}"
            ) from exc
        headway = normalize.integer(
            normalize.required(row, "headway_secs"), "headway_secs", minimum=1
        )
        exact_value = row.get("exact_times", "")
        if exact_value not in {"", "0", "1"}:
            raise InvalidGTFSFeedError(
                f"Invalid exact_times value for trip {identifier!r}: {exact_value!r}"
            )
        if start >= end:
            raise InvalidGTFSFeedError(
                f"Frequency start_time must be earlier than end_time for trip {identifier!r}."
            )
        windows[identifier].append((start, end, headway, exact_value == "1"))

    grouped_times: dict[str, list[StopTime]] = defaultdict(list)
    for item in stop_times:
        grouped_times[item.trip_id].append(item)

    expanded_trips: dict[str, Trip] = {}
    expanded_times: list[StopTime] = []
    existing_ids = set(trips)
    generated_count = 0
    generated_stop_time_count = 0
    for identifier, trip in trips.items():
        trip_windows = windows.get(identifier, [])
        if not trip_windows:
            expanded_trips[identifier] = trip
            expanded_times.extend(grouped_times[identifier])
            continue

        exact_windows = [window for window in trip_windows if window[3]]
        if len(exact_windows) != len(trip_windows):
            expanded_trips[identifier] = trip
            expanded_times.extend(grouped_times[identifier])

        if not exact_windows:
            continue

        template_times = sorted(grouped_times[identifier], key=lambda item: item.sequence)
        if not template_times:
            raise InvalidGTFSFeedError(
                f"Cannot expand frequency trip {identifier!r} without stop times."
            )
        first_time = template_times[0].departure_seconds
        if first_time is None:
            first_time = template_times[0].arrival_seconds
        if first_time is None:
            raise InvalidGTFSFeedError(
                f"Cannot expand frequency trip {identifier!r} without a first-stop time."
            )

        for start, end, headway, _ in exact_windows:
            for departure in range(start, end, headway):
                generated_count += 1
                if generated_count > MAX_EXPANDED_TRIPS:
                    raise InvalidGTFSFeedError(
                        f"Frequency expansion exceeds {MAX_EXPANDED_TRIPS} generated trips."
                    )
                generated_id = f"{identifier}@{departure}"
                if generated_id in existing_ids:
                    raise InvalidGTFSFeedError(
                        f"Generated frequency trip ID collides with existing ID: {generated_id!r}."
                    )
                existing_ids.add(generated_id)
                offset = departure - first_time
                expanded_trips[generated_id] = replace(trip, id=generated_id)
                for item in template_times:
                    generated_stop_time_count += 1
                    if generated_stop_time_count > MAX_EXPANDED_STOP_TIMES:
                        raise InvalidGTFSFeedError(
                            "Frequency expansion exceeds "
                            f"{MAX_EXPANDED_STOP_TIMES} generated stop times."
                        )
                    arrival = (
                        item.arrival_seconds + offset if item.arrival_seconds is not None else None
                    )
                    departure_time = (
                        item.departure_seconds + offset
                        if item.departure_seconds is not None
                        else None
                    )
                    if (arrival is not None and arrival < 0) or (
                        departure_time is not None and departure_time < 0
                    ):
                        raise InvalidGTFSFeedError(
                            f"Frequency shift creates a negative time for trip {identifier!r}."
                        )
                    expanded_times.append(
                        replace(
                            item,
                            trip_id=generated_id,
                            arrival_seconds=arrival,
                            departure_seconds=departure_time,
                        )
                    )

    return expanded_trips, expanded_times


def select_network(
    feed: "GTFSFeed",
    *,
    route_types: frozenset[int],
    on: date | None = None,
    expand_frequencies: bool = False,
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
    if expand_frequencies:
        trips, times = _expand_frequencies(
            trips,
            times,
            list(feed.rows("frequencies.txt")),
        )
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
