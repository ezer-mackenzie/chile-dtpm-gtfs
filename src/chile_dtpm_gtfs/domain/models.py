"""Immutable transit models independent of CSV and exporter implementations."""

from dataclasses import dataclass
from datetime import date

from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError


@dataclass(frozen=True, slots=True)
class Agency:
    """A transit operator; a single agency may have an empty GTFS identifier."""

    id: str
    name: str
    url: str
    timezone: str


@dataclass(frozen=True, slots=True)
class Stop:
    """A GTFS location, retaining its explicit parent and location type."""

    id: str
    name: str
    latitude: float | None
    longitude: float | None
    location_type: int
    parent_station: str | None
    level_id: str | None = None
    platform_code: str | None = None


@dataclass(frozen=True, slots=True)
class Station(Stop):
    """An explicitly declared GTFS station (location_type=1)."""


@dataclass(frozen=True, slots=True)
class Platform(Stop):
    """A boarding stop with a parent station (location_type=0)."""


@dataclass(frozen=True, slots=True)
class Entrance(Stop):
    """A station entrance/exit (location_type=2)."""


@dataclass(frozen=True, slots=True)
class Route:
    """A route; geometry variants are linked through trips, never collapsed."""

    id: str
    agency_id: str
    short_name: str
    long_name: str
    route_type: int
    color: str | None = None
    text_color: str | None = None


@dataclass(frozen=True, slots=True)
class Trip:
    """One scheduled trip or a frequency template."""

    id: str
    route_id: str
    service_id: str
    direction_id: int | None
    shape_id: str | None
    headsign: str | None = None


@dataclass(frozen=True, slots=True)
class StopTime:
    """A stop visit with optional arrival/departure service seconds."""

    trip_id: str
    stop_id: str
    sequence: int
    arrival_seconds: int | None
    departure_seconds: int | None


@dataclass(frozen=True, slots=True)
class ShapePoint:
    """An original shape point; sequence determines geographic order."""

    latitude: float
    longitude: float
    sequence: int
    distance_traveled: float | None = None


@dataclass(frozen=True, slots=True)
class Shape:
    """All ordered points for one shape identifier."""

    id: str
    points: tuple[ShapePoint, ...]


@dataclass(frozen=True, slots=True)
class ServiceException:
    """An explicit addition or removal on a service date."""

    on: date
    added: bool


@dataclass(frozen=True, slots=True)
class Service:
    """Weekly applicability plus calendar_dates overrides."""

    id: str
    start_date: date | None
    end_date: date | None
    weekdays: tuple[bool, ...]
    exceptions: tuple[ServiceException, ...]

    def is_active(self, on: date) -> bool:
        """Apply exceptions before the weekly calendar; unknown calendars raise."""
        for exception in self.exceptions:
            if exception.on == on:
                return exception.added
        if self.start_date is not None and self.end_date is not None:
            return self.start_date <= on <= self.end_date and self.weekdays[on.weekday()]
        if self.exceptions:
            return False
        raise InvalidGTFSFeedError(f"No calendar data for service {self.id!r}.")
