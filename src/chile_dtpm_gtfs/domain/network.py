"""A materialized subset that no longer depends on an open archive."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chile_dtpm_gtfs.exporters.base import JSONValue

from chile_dtpm_gtfs.domain.models import (
    Agency,
    Entrance,
    Platform,
    Route,
    Service,
    Shape,
    Station,
    Stop,
    StopTime,
    Trip,
)
from chile_dtpm_gtfs.gtfs.metadata import FeedMetadata


@dataclass(frozen=True, slots=True)
class TransitNetwork:
    """Normalized route subset; stop_times and trips are scheduled templates."""

    metadata: FeedMetadata
    agencies: tuple[Agency, ...]
    routes: tuple[Route, ...]
    trips: tuple[Trip, ...]
    stops: tuple[Stop, ...]
    stop_times: tuple[StopTime, ...]
    shapes: tuple[Shape, ...]
    services: tuple[Service, ...]

    @property
    def stations(self) -> tuple[Station, ...]:
        """Explicit parent stations only; do not invent missing station hierarchy."""
        return tuple(stop for stop in self.stops if isinstance(stop, Station))

    @property
    def platforms(self) -> tuple[Platform, ...]:
        """Boarding platforms with a declared parent station."""
        return tuple(stop for stop in self.stops if isinstance(stop, Platform))

    @property
    def entrances(self) -> tuple[Entrance, ...]:
        """Entrances belonging to selected station hierarchies."""
        return tuple(stop for stop in self.stops if isinstance(stop, Entrance))

    def to_geojson(self) -> dict[str, JSONValue]:
        """Export original locations and all route shape variants in memory."""
        from chile_dtpm_gtfs.exporters.geojson import GeoJSONExporter

        return GeoJSONExporter().to_dict(self)

    def write_geojson(self, path: str | Path, *, overwrite: bool = False) -> Path:
        """Write GeoJSON atomically; replacing an existing file is opt-in."""
        from chile_dtpm_gtfs.exporters.base import write_document

        return write_document(self.to_geojson(), path, overwrite=overwrite)
