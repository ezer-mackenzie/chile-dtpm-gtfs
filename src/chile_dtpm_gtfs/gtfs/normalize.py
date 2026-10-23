"""Convert string records into typed domain values with useful errors."""

import math
from collections.abc import Iterable

from chile_dtpm_gtfs.domain.models import (
    Agency,
    Entrance,
    Level,
    Pathway,
    Platform,
    Route,
    Station,
    Stop,
    StopTime,
    Trip,
)
from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError
from chile_dtpm_gtfs.gtfs.time import parse_service_time


def required(row: dict[str, str], key: str) -> str:
    """Read a nonempty required value."""
    value = row.get(key, "")
    if not value:
        raise InvalidGTFSFeedError(f"Missing required value {key!r} in {row!r}")
    return value


def integer(value: str, field: str, *, minimum: int = 0) -> int:
    """Read a nonnegative ASCII integer."""
    if not value.isascii() or not value.isdigit() or int(value) < minimum:
        raise InvalidGTFSFeedError(f"Invalid {field}: {value!r}")
    return int(value)


def number(value: str, field: str) -> float:
    """Read a finite numeric value."""
    try:
        result = float(value)
    except ValueError as exc:
        raise InvalidGTFSFeedError(f"Invalid {field}: {value!r}") from exc
    if not math.isfinite(result):
        raise InvalidGTFSFeedError(f"Nonfinite {field}: {value!r}")
    return result


def coordinates(row: dict[str, str], lat: str, lon: str) -> tuple[float | None, float | None]:
    """Read a WGS84 pair, preserving missing coordinates as None."""
    latitude, longitude = row.get(lat, ""), row.get(lon, "")
    if not latitude and not longitude:
        return None, None
    y, x = number(latitude, lat), number(longitude, lon)
    if not -90 <= y <= 90 or not -180 <= x <= 180:
        raise InvalidGTFSFeedError(f"Coordinates outside WGS84 bounds: {latitude}, {longitude}")
    return y, x


def unique[T](items: Iterable[T], key: str = "id") -> dict[str, T]:
    """Index domain entities and reject duplicate identifiers."""
    result: dict[str, T] = {}
    for item in items:
        identifier = str(getattr(item, key))
        if identifier in result:
            raise InvalidGTFSFeedError(
                f"Duplicate {type(item).__name__} identifier: {identifier!r}"
            )
        result[identifier] = item
    return result


def agency(row: dict[str, str]) -> Agency:
    """Normalize one agency."""
    return Agency(
        row.get("agency_id", ""),
        required(row, "agency_name"),
        required(row, "agency_url"),
        required(row, "agency_timezone"),
    )


def route(row: dict[str, str], agencies: dict[str, Agency]) -> Route:
    """Resolve the optional agency identifier when exactly one agency exists."""
    agency_id = row.get("agency_id", "")
    if not agency_id and len(agencies) == 1:
        agency_id = next(iter(agencies))
    if agency_id not in agencies:
        raise InvalidGTFSFeedError(
            f"Unknown agency {agency_id!r} for route {row.get('route_id')!r}"
        )
    short, long = row.get("route_short_name", ""), row.get("route_long_name", "")
    if not short and not long:
        raise InvalidGTFSFeedError("A route needs a short or long name.")
    return Route(
        required(row, "route_id"),
        agency_id,
        short,
        long,
        integer(required(row, "route_type"), "route_type"),
        row.get("route_color") or None,
        row.get("route_text_color") or None,
    )


def trip(row: dict[str, str]) -> Trip:
    """Normalize a trip, keeping shape and direction optional."""
    direction = row.get("direction_id", "")
    if direction not in {"", "0", "1"}:
        raise InvalidGTFSFeedError(f"Invalid direction_id: {direction!r}")
    return Trip(
        required(row, "trip_id"),
        required(row, "route_id"),
        required(row, "service_id"),
        int(direction) if direction else None,
        row.get("shape_id") or None,
        row.get("trip_headsign") or None,
    )


def stop(row: dict[str, str]) -> Stop:
    """Choose a location class from GTFS type and parent, never its name."""
    kind = integer(row.get("location_type") or "0", "location_type")
    if kind not in range(5):
        raise InvalidGTFSFeedError(f"Invalid location_type: {kind}")
    parent = row.get("parent_station") or None
    latitude, longitude = coordinates(row, "stop_lat", "stop_lon")
    cls = (
        Station
        if kind == 1
        else Entrance
        if kind == 2
        else Platform
        if kind == 0 and parent
        else Stop
    )
    return cls(
        required(row, "stop_id"),
        row.get("stop_name", ""),
        latitude,
        longitude,
        kind,
        parent,
        row.get("level_id") or None,
        row.get("platform_code") or None,
    )


def stop_time(row: dict[str, str]) -> StopTime:
    """Convert optional times into seconds without assuming a 24-hour clock."""
    arrival, departure = row.get("arrival_time", ""), row.get("departure_time", "")
    return StopTime(
        required(row, "trip_id"),
        required(row, "stop_id"),
        integer(required(row, "stop_sequence"), "stop_sequence"),
        parse_service_time(arrival) if arrival else None,
        parse_service_time(departure) if departure else None,
    )


def level(row: dict[str, str]) -> Level:
    """Normalize a declared GTFS level."""
    return Level(
        required(row, "level_id"),
        number(required(row, "level_index"), "level_index"),
        row.get("level_name") or None,
    )


def pathway(row: dict[str, str]) -> Pathway:
    """Normalize one declared pathway without deriving additional connections."""
    bidirectional = required(row, "is_bidirectional")
    if bidirectional not in {"0", "1"}:
        raise InvalidGTFSFeedError(f"Invalid is_bidirectional: {bidirectional!r}")
    mode = integer(required(row, "pathway_mode"), "pathway_mode", minimum=1)
    if mode > 7:
        raise InvalidGTFSFeedError(f"Invalid pathway_mode: {mode}")
    stairs = row.get("stair_count", "")
    if stairs:
        stair_digits = stairs[1:] if stairs.startswith("-") else stairs
        if not stair_digits or not stair_digits.isascii() or not stair_digits.isdigit():
            raise InvalidGTFSFeedError(f"Invalid stair_count: {stairs!r}")
    return Pathway(
        required(row, "pathway_id"),
        required(row, "from_stop_id"),
        required(row, "to_stop_id"),
        mode,
        bidirectional == "1",
        number(row["length"], "length") if row.get("length") else None,
        integer(row["traversal_time"], "traversal_time") if row.get("traversal_time") else None,
        int(stairs) if stairs else None,
        number(row["max_slope"], "max_slope") if row.get("max_slope") else None,
        number(row["min_width"], "min_width") if row.get("min_width") else None,
        row.get("signposted_as") or None,
        row.get("reversed_signposted_as") or None,
    )
