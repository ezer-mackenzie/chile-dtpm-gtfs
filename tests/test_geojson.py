"""GeoJSON preserves geographic data and remains independent of archive lifetime."""

import json
from pathlib import Path

import pytest
from conftest import write_archive

from chile_dtpm_gtfs import GTFSFeed
from chile_dtpm_gtfs.exceptions import FeedExportError


def test_geojson_variants_and_coordinates(archive_path: Path, tmp_path: Path) -> None:
    with GTFSFeed.from_file(archive_path) as feed:
        metro = feed.metro()
    path = metro.write_geojson(tmp_path / "metro.geojson")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document == metro.to_geojson()
    assert document["type"] == "FeatureCollection"
    features = document["features"]
    assert len(features) == 6
    lines = [item for item in features if item["properties"]["kind"] == "route"]
    assert {item["properties"]["shape_id"] for item in lines} == {"A", "Z"}
    assert lines[0]["geometry"]["coordinates"] == [[-70.65, -33.45], [-70.66, -33.46]]
    assert lines[1]["geometry"]["coordinates"] == [[-70.66, -33.46], [-70.65, -33.45]]
    assert lines[0]["properties"]["trip_ids"] == ["T"]
    assert lines[1]["properties"]["direction_ids"] == [1]
    station = next(item for item in features if item["id"] == "stop:S")
    assert station["geometry"] == {"type": "Point", "coordinates": [-70.65, -33.45]}
    assert document["metadata"]["sha256"] == metro.metadata.sha256
    assert len({item["id"] for item in features}) == len(features)


def test_no_shapes_uses_null_geometry(tmp_path: Path, tables: dict[str, str]) -> None:
    del tables["shapes.txt"]
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        document = json.loads(json.dumps(feed.metro().to_geojson()))
    lines = [item for item in document["features"] if item["properties"]["kind"] == "route"]
    assert all(item["geometry"] is None for item in lines)
    assert {item["properties"]["shape_id"] for item in lines} == {"A", "Z"}


def test_missing_location_coordinates_are_null(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["stops.txt"] = tables["stops.txt"].replace("-33.451,-70.651", ",")
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        document = json.loads(json.dumps(feed.metro().to_geojson()))
    platform = next(item for item in document["features"] if item["id"] == "stop:P")
    assert platform["geometry"] is None


def test_output_replacement_is_explicit(archive_path: Path, tmp_path: Path) -> None:
    with GTFSFeed.from_file(archive_path) as feed:
        metro = feed.metro()
    output = tmp_path / "metro.geojson"
    output.write_text("original", encoding="utf-8")
    with pytest.raises(FeedExportError, match="already exists"):
        metro.write_geojson(output)
    assert output.read_text() == "original"
    metro.write_geojson(output, overwrite=True)
    assert json.loads(output.read_text())["type"] == "FeatureCollection"
    assert list(tmp_path.glob("*.part")) == []


def test_short_shape_cannot_be_a_linestring(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["shapes.txt"] = tables["shapes.txt"].replace("Z,-33.45,-70.65,2\n", "")
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        with pytest.raises(FeedExportError, match="at least two"):
            feed.metro().write_geojson(tmp_path / "metro.geojson")
    assert not (tmp_path / "metro.geojson").exists()
