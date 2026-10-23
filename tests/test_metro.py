"""Domain selection must follow IDs and preserve original relationships."""

from datetime import date
from pathlib import Path

import pytest
from conftest import write_archive

from chile_dtpm_gtfs import GTFSFeed
from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError


def test_metro_relationships(archive_path: Path) -> None:
    with GTFSFeed.from_file(archive_path) as feed:
        metro = feed.metro()
    assert [route.id for route in metro.routes] == ["R"]
    assert [trip.id for trip in metro.trips] == ["T", "U"]
    assert {stop.id for stop in metro.stops} == {"S", "P", "E", "Q"}
    assert [station.id for station in metro.stations] == ["S"]
    assert [platform.id for platform in metro.platforms] == ["P"]
    assert [entrance.id for entrance in metro.entrances] == ["E"]
    assert {shape.id for shape in metro.shapes} == {"A", "Z"}
    assert metro.shapes[0].points[0].longitude == -70.65
    assert metro.shapes[0].points[0].sequence == 1
    assert metro.stop_times[0].arrival_seconds == 90600
    assert {trip.direction_id for trip in metro.trips} == {0, 1}


def test_generic_route_selection(archive_path: Path) -> None:
    with GTFSFeed.from_file(archive_path) as feed:
        buses = feed.select(route_types=frozenset({3}))
        empty = feed.select(route_types=frozenset({999}))
    assert {stop.id for stop in buses.stops} == {"B"}
    assert empty.routes == empty.stops == empty.shapes == ()


def test_calendar_exceptions_override_week(archive_path: Path) -> None:
    with GTFSFeed.from_file(archive_path) as feed:
        assert len(feed.metro(on=date(2026, 9, 13)).trips) == 2  # Added Sunday.
        assert feed.metro(on=date(2026, 9, 14)).trips == ()  # Removed Monday.
        assert len(feed.metro(on=date(2026, 9, 15)).trips) == 2
        assert feed.metro(on=date(2027, 1, 1)).trips == ()


def test_exception_only_calendar(tmp_path: Path, tables: dict[str, str]) -> None:
    del tables["calendar.txt"]
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        assert len(feed.metro(on=date(2026, 9, 13)).trips) == 2
        assert feed.metro(on=date(2026, 9, 15)).trips == ()


def test_unknown_calendar_is_explicit(tmp_path: Path, tables: dict[str, str]) -> None:
    del tables["calendar.txt"]
    del tables["calendar_dates.txt"]
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        assert len(feed.metro().trips) == 2
        with pytest.raises(InvalidGTFSFeedError, match="No calendar data"):
            feed.metro(on=date(2026, 9, 15))


def test_absent_shapes_preserve_trip_references(tmp_path: Path, tables: dict[str, str]) -> None:
    del tables["shapes.txt"]
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        metro = feed.metro()
    assert metro.shapes == ()
    assert {trip.shape_id for trip in metro.trips} == {"A", "Z"}


def test_declared_pathways_and_levels_are_normalized(
    tmp_path: Path, tables: dict[str, str]
) -> None:
    lines = tables["stops.txt"].splitlines()
    tables["stops.txt"] = (
        "\n".join(
            [lines[0] + ",level_id"]
            + [line + (",PLATFORM" if line.startswith(("P,", "Q,")) else ",") for line in lines[1:]]
        )
        + "\n"
    )
    tables["levels.txt"] = "level_id,level_index,level_name\nPLATFORM,0,Platform\n"
    tables["pathways.txt"] = (
        "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional,"
        "length,traversal_time,stair_count,max_slope,min_width,signposted_as,"
        "reversed_signposted_as\n"
        "P1,P,Q,1,1,20.5,30,-4,0.05,1.2,North entrance,South exit\n"
        "P2,B,P,1,0,,,,,,,\n"
    )
    with GTFSFeed.from_file(write_archive(tmp_path / "station-detail.zip", tables)) as feed:
        network = feed.metro()

    assert [(level.id, level.index, level.name) for level in network.levels] == [
        ("PLATFORM", 0.0, "Platform")
    ]
    assert len(network.pathways) == 1
    pathway = network.pathways[0]
    assert pathway.id == "P1"
    assert (pathway.from_stop_id, pathway.to_stop_id, pathway.mode) == ("P", "Q", 1)
    assert pathway.is_bidirectional
    assert pathway.stair_count == -4
    assert pathway.signposted_as == "North entrance"


def test_missing_referenced_level_is_explicit(tmp_path: Path, tables: dict[str, str]) -> None:
    lines = tables["stops.txt"].splitlines()
    tables["stops.txt"] = (
        "\n".join(
            [lines[0] + ",level_id"]
            + [line + (",MISSING" if line.startswith("P,") else ",") for line in lines[1:]]
        )
        + "\n"
    )
    with GTFSFeed.from_file(write_archive(tmp_path / "missing-level.zip", tables)) as feed:
        with pytest.raises(InvalidGTFSFeedError, match="Referenced levels are missing"):
            feed.metro()


@pytest.mark.parametrize(
    "table,old,new",
    [
        ("trips.txt", "R,WK,T", "missing,WK,T"),
        ("stop_times.txt", "T,25:10:00,25:11:00,P", "T,25:10:00,25:11:00,missing"),
        ("stops.txt", "0,S", "0,missing"),
        ("stops.txt", "1,\n", "1,P\n"),
        ("stops.txt", "-33.451", "NaN"),
        ("stops.txt", "-70.651", "200"),
        ("calendar.txt", "WK,1,1", "WK,2,1"),
        ("trips.txt", "0,A", "7,A"),
        ("routes.txt", "R,M,L1", "R,missing,L1"),
        ("shapes.txt", "Z,-33.45,-70.65,2", "Z,-33.45,-70.65,1"),
    ],
)
def test_bad_domain_records(
    tmp_path: Path,
    tables: dict[str, str],
    table: str,
    old: str,
    new: str,
) -> None:
    tables[table] = tables[table].replace(old, new)
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        with pytest.raises(InvalidGTFSFeedError):
            feed.metro()


def test_duplicate_ids(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["trips.txt"] += "R,WK,T,0,A\n"
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        with pytest.raises(InvalidGTFSFeedError, match="Duplicate"):
            feed.metro()


def test_duplicate_stop_sequence(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["stop_times.txt"] += "T,26:00:00,26:00:00,P,1\n"
    with GTFSFeed.from_file(write_archive(tmp_path / "feed.zip", tables)) as feed:
        with pytest.raises(InvalidGTFSFeedError, match="Duplicate stop sequence"):
            feed.metro()
