"""Deterministic JSON export for normalized transit snapshots."""

from chile_dtpm_gtfs.domain.models import (
    Agency,
    Level,
    Pathway,
    Route,
    Service,
    Shape,
    Stop,
    StopTime,
    Trip,
)
from chile_dtpm_gtfs.domain.network import TransitNetwork
from chile_dtpm_gtfs.exporters.base import JSONValue
from chile_dtpm_gtfs.exporters.geojson import metadata_dict


class NormalizedJSONExporter:
    """Serialize domain records with explicit ISO dates and nullable fields."""

    def to_dict(self, network: TransitNetwork) -> dict[str, JSONValue]:
        """Return a versioned document independent of source CSV serialization."""
        return {
            "schema_version": 1,
            "metadata": metadata_dict(network.metadata),
            "agencies": [self._agency(item) for item in network.agencies],
            "routes": [self._route(item) for item in network.routes],
            "trips": [self._trip(item) for item in network.trips],
            "stops": [self._stop(item) for item in network.stops],
            "stop_times": [self._stop_time(item) for item in network.stop_times],
            "shapes": [self._shape(item) for item in network.shapes],
            "services": [self._service(item) for item in network.services],
            "levels": [self._level(item) for item in network.levels],
            "pathways": [self._pathway(item) for item in network.pathways],
        }

    @staticmethod
    def _agency(item: Agency) -> dict[str, JSONValue]:
        return {
            "id": item.id,
            "name": item.name,
            "url": item.url,
            "timezone": item.timezone,
        }

    @staticmethod
    def _route(item: Route) -> dict[str, JSONValue]:
        return {
            "id": item.id,
            "agency_id": item.agency_id,
            "short_name": item.short_name,
            "long_name": item.long_name,
            "route_type": item.route_type,
            "color": item.color,
            "text_color": item.text_color,
        }

    @staticmethod
    def _trip(item: Trip) -> dict[str, JSONValue]:
        return {
            "id": item.id,
            "route_id": item.route_id,
            "service_id": item.service_id,
            "direction_id": item.direction_id,
            "shape_id": item.shape_id,
            "headsign": item.headsign,
        }

    @staticmethod
    def _stop(item: Stop) -> dict[str, JSONValue]:
        return {
            "id": item.id,
            "name": item.name,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "location_type": item.location_type,
            "parent_station": item.parent_station,
            "level_id": item.level_id,
            "platform_code": item.platform_code,
        }

    @staticmethod
    def _stop_time(item: StopTime) -> dict[str, JSONValue]:
        return {
            "trip_id": item.trip_id,
            "stop_id": item.stop_id,
            "sequence": item.sequence,
            "arrival_seconds": item.arrival_seconds,
            "departure_seconds": item.departure_seconds,
        }

    @staticmethod
    def _shape(item: Shape) -> dict[str, JSONValue]:
        return {
            "id": item.id,
            "points": [
                {
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                    "sequence": point.sequence,
                    "distance_traveled": point.distance_traveled,
                }
                for point in item.points
            ],
        }

    @staticmethod
    def _service(item: Service) -> dict[str, JSONValue]:
        return {
            "id": item.id,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "end_date": item.end_date.isoformat() if item.end_date else None,
            "weekdays": list(item.weekdays),
            "exceptions": [
                {"on": exception.on.isoformat(), "added": exception.added}
                for exception in item.exceptions
            ],
        }

    @staticmethod
    def _level(item: Level) -> dict[str, JSONValue]:
        return {"id": item.id, "index": item.index, "name": item.name}

    @staticmethod
    def _pathway(item: Pathway) -> dict[str, JSONValue]:
        return {
            "id": item.id,
            "from_stop_id": item.from_stop_id,
            "to_stop_id": item.to_stop_id,
            "mode": item.mode,
            "is_bidirectional": item.is_bidirectional,
            "length": item.length,
            "traversal_time": item.traversal_time,
            "stair_count": item.stair_count,
            "max_slope": item.max_slope,
            "min_width": item.min_width,
            "signposted_as": item.signposted_as,
            "reversed_signposted_as": item.reversed_signposted_as,
        }
