# GeoJSON export

```python
from chile_dtpm_gtfs import GTFSFeed

with GTFSFeed.from_file("GTFS.zip") as feed:
    metro = feed.metro()

document = metro.to_geojson()
metro.write_geojson("metro.geojson")
```

Both entry points use `GeoJSONExporter` on a `TransitNetwork`; export never reads
a GTFS table or accesses the network. The exporter contract is defined in
`exporters.base.Exporter`, allowing future formats without duplicating parsing.
No additional geographic or JSON dependency is required for this initial format.

The FeatureCollection contains one feature per selected location and one feature
per route/shape pair. Shared shapes stay associated with each route that uses them.
Route properties retain IDs, names, colors, shape ID, and the corresponding trip,
service, and direction IDs. Stop properties retain ID, name, location type, parent,
level, and platform code. Feature IDs escape identifier components and are stable
for the same snapshot. Provenance is stored in the collection's `metadata` foreign
member; it includes archive SHA-256 and available source/coverage information.

Point and LineString positions are `[longitude, latitude]` in WGS84. Point order
follows numeric shape sequence without smoothing or simplification. A referenced
but unavailable shape produces null geometry, as does a location with no
coordinates. Routes with no selected trips remain metadata features with null
geometry. Shapes with fewer than two points cannot form a LineString and raise
`FeedExportError`. The exporter does not derive routes from stop coordinates.

`write_geojson(path, overwrite=False)` requires an existing parent directory and
writes UTF-8 JSON atomically. Existing output requires explicit `overwrite=True`.
Failed writes do not replace the existing destination. JSON NaN/Infinity values
are rejected. TopoJSON, runtime JSON, and per-collection exports are deferred.

Format reference: [RFC 7946](https://www.rfc-editor.org/rfc/rfc7946).
