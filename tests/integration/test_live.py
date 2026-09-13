"""Opt-in network acceptance test; ordinary test runs never contact DTPM."""

import json
import os
from pathlib import Path

import pytest

from chile_dtpm_gtfs import DTPM


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("DTPM_LIVE_TESTS") != "1", reason="Set DTPM_LIVE_TESTS=1 to contact DTPM"
)
def test_official_feed_to_geojson(tmp_path: Path) -> None:
    publication = DTPM().current()
    with publication.download() as feed:
        report = feed.validate()
        assert report.row_counts["routes.txt"] > 0
        metro = feed.metro()
        assert metro.routes
        assert all(route.route_type == 1 for route in metro.routes)
        assert metro.stops
        assert metro.shapes
        output = metro.write_geojson(tmp_path / "metro.geojson")
        document = json.loads(output.read_text(encoding="utf-8"))
        assert document["type"] == "FeatureCollection"
        assert document["metadata"]["source_url"] == publication.download_url
        assert document["metadata"]["sha256"] == feed.metadata.sha256
        assert len(document["features"]) >= len(metro.stops)
