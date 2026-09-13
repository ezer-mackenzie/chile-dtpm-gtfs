"""GeoJSON FeatureCollections preserving route variants and source coordinates."""

from collections import defaultdict
from urllib.parse import quote

from chile_dtpm_gtfs.domain.models import Trip
from chile_dtpm_gtfs.domain.network import TransitNetwork
from chile_dtpm_gtfs.exceptions import FeedExportError
from chile_dtpm_gtfs.exporters.base import JSONValue
from chile_dtpm_gtfs.gtfs.metadata import FeedMetadata


def metadata_dict(metadata: FeedMetadata) -> dict[str, JSONValue]:
    """Serialize provenance explicitly, with ISO dates and UTC timestamps."""
    return {
        "sha256": metadata.sha256,
        "original_filename": metadata.original_filename,
        "source_url": metadata.source_url,
        "resolved_url": metadata.resolved_url,
        "source_page": metadata.source_page,
        "size_bytes": metadata.size_bytes,
        "content_length": metadata.content_length,
        "downloaded_at": metadata.downloaded_at.isoformat() if metadata.downloaded_at else None,
        "published_effective_from": metadata.published_effective_from.isoformat()
        if metadata.published_effective_from
        else None,
        "feed_start_date": metadata.feed_start_date.isoformat()
        if metadata.feed_start_date
        else None,
        "feed_end_date": metadata.feed_end_date.isoformat() if metadata.feed_end_date else None,
        "feed_version": metadata.feed_version,
    }


class GeoJSONExporter:
    """Produce one point per location and one feature per route/shape combination."""

    def to_dict(self, network: TransitNetwork) -> dict[str, JSONValue]:
        """Return RFC 7946 GeoJSON with provenance as a foreign member.

        Missing geometry is null. Existing shapes must have at least two points;
        no smoothing, coordinate projection, or invented line segments are used.
        """
        features: list[JSONValue] = []
        for stop in network.stops:
            geometry: JSONValue = None
            if stop.longitude is not None and stop.latitude is not None:
                geometry = {"type": "Point", "coordinates": [stop.longitude, stop.latitude]}
            features.append(
                {
                    "type": "Feature",
                    "id": f"stop:{quote(stop.id, safe='')}",
                    "geometry": geometry,
                    "properties": {
                        "kind": "stop",
                        "stop_id": stop.id,
                        "name": stop.name,
                        "location_type": stop.location_type,
                        "parent_station": stop.parent_station,
                        "level_id": stop.level_id,
                        "platform_code": stop.platform_code,
                    },
                }
            )
        groups: dict[str, dict[str | None, list[Trip]]] = defaultdict(lambda: defaultdict(list))
        for trip in network.trips:
            groups[trip.route_id][trip.shape_id].append(trip)
        shapes = {shape.id: shape for shape in network.shapes}
        for route in network.routes:
            variants = groups[route.id] or {None: []}
            for shape_id in sorted(variants, key=lambda value: value or ""):
                trips = variants[shape_id]
                shape = shapes.get(shape_id) if shape_id else None
                geometry = None
                if shape is not None:
                    if len(shape.points) < 2:
                        raise FeedExportError(
                            f"Shape {shape.id!r} needs at least two points for a LineString."
                        )
                    geometry = {
                        "type": "LineString",
                        "coordinates": [
                            [point.longitude, point.latitude] for point in shape.points
                        ],
                    }
                features.append(
                    {
                        "type": "Feature",
                        "id": f"route:{quote(route.id, safe='')}:{quote(shape_id or '', safe='')}",
                        "geometry": geometry,
                        "properties": {
                            "kind": "route",
                            "route_id": route.id,
                            "agency_id": route.agency_id,
                            "short_name": route.short_name,
                            "long_name": route.long_name,
                            "route_type": route.route_type,
                            "color": route.color,
                            "text_color": route.text_color,
                            "shape_id": shape_id,
                            "trip_ids": [trip.id for trip in trips],
                            "direction_ids": list(
                                sorted(
                                    {
                                        trip.direction_id
                                        for trip in trips
                                        if trip.direction_id is not None
                                    }
                                )
                            ),
                            "service_ids": list(sorted({trip.service_id for trip in trips})),
                        },
                    }
                )
        return {
            "type": "FeatureCollection",
            "metadata": metadata_dict(network.metadata),
            "features": features,
        }
