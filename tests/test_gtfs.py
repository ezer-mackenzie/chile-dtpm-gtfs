"""Local archive, metadata, validation, and resource ownership contracts."""

import hashlib
from datetime import date
from pathlib import Path

import httpx
import pytest
from conftest import write_archive

from chile_dtpm_gtfs import FeedPublication, GTFSFeed
from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError
from chile_dtpm_gtfs.gtfs.time import parse_service_time


def test_local_feed(archive_path: Path) -> None:
    with GTFSFeed.from_file(archive_path) as feed:
        assert len(list(feed.rows("routes.txt"))) == 2
        assert list(feed.rows("pathways.txt")) == []
        assert feed.metadata.sha256 == hashlib.sha256(archive_path.read_bytes()).hexdigest()
        assert feed.metadata.source_url is None
        assert feed.metadata.feed_version == "test-version"
        assert feed.metadata.feed_start_date == date(2026, 1, 1)
        report = feed.validate()
        assert report.valid
        assert report.row_counts["stop_times.txt"] == 5
    assert archive_path.exists()
    with pytest.raises(InvalidGTFSFeedError, match="closed"):
        list(feed.rows("stops.txt"))


def test_publication_download_owns_temporary_archive(archive_path: Path) -> None:
    publication = FeedPublication(
        "Test", date(2026, 8, 29), "https://example.org/feed.zip", "feed.zip"
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=archive_path.read_bytes())
    )
    with publication.download(transport=transport) as feed:
        path = feed.path
        assert path.exists()
        assert feed.metadata.published_effective_from == date(2026, 8, 29)
        assert feed.metadata.feed_start_date == date(2026, 1, 1)
        assert feed.metadata.source_page == publication.source_page
        assert feed.metadata.source_url == publication.download_url
        assert feed.metadata.downloaded_at is not None
    assert not path.exists()


def test_download_explicit_destination(archive_path: Path, tmp_path: Path) -> None:
    destination = tmp_path / "retained.zip"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=archive_path.read_bytes())
    )
    with GTFSFeed.from_url(
        "https://example.org/feed.zip", destination=destination, transport=transport
    ) as feed:
        assert feed.path == destination
    assert destination.exists()


@pytest.mark.parametrize(
    "missing", ["agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
)
def test_missing_required_files(tmp_path: Path, tables: dict[str, str], missing: str) -> None:
    del tables[missing]
    with pytest.raises(InvalidGTFSFeedError, match="Missing required"):
        GTFSFeed.from_file(write_archive(tmp_path / "invalid.zip", tables))


def test_optional_files_are_optional(tmp_path: Path, tables: dict[str, str]) -> None:
    core = {
        name: tables[name]
        for name in ("agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt")
    }
    with GTFSFeed.from_file(write_archive(tmp_path / "minimal.zip", core)) as feed:
        assert feed.metadata.feed_version is None
        assert feed.validate().row_counts["routes.txt"] == 2


def test_bus_and_rail_selectors_use_standard_route_types(archive_path: Path) -> None:
    with GTFSFeed.from_file(archive_path) as feed:
        bus = feed.bus()
        rail = feed.rail()

    assert [route.id for route in bus.routes] == ["B"]
    assert [route.id for route in rail.routes] == ["R"]


def test_bus_and_rail_selectors_preserve_generic_route_type_selection(
    tmp_path: Path, tables: dict[str, str]
) -> None:
    tables["routes.txt"] += "T,M,Trolleybus,Electric bus,11,\nL,M,Light rail,Light rail,0,\n"
    tables["trips.txt"] += "T,WK,TRIP_T,0,\nL,WK,TRIP_L,0,\n"
    tables["stop_times.txt"] += "TRIP_T,09:00:00,09:00:00,P,3\nTRIP_L,09:00:00,09:00:00,P,3\n"
    for route_type in (2, 5, 6, 7, 12):
        identifier = f"RAIL_{route_type}"
        tables["routes.txt"] += f"{identifier},M,Rail {route_type},Rail,{route_type},\n"
        tables["trips.txt"] += f"{identifier},WK,TRIP_{identifier},0,\n"
        tables["stop_times.txt"] += f"TRIP_{identifier},09:00:00,09:00:00,P,3\n"
    with GTFSFeed.from_file(write_archive(tmp_path / "modes.zip", tables)) as feed:
        assert {route.route_type for route in feed.bus().routes} == {3, 11}
        assert {route.route_type for route in feed.rail().routes} == {0, 1, 2, 5, 6, 7, 12}
        assert {route.route_type for route in feed.select(route_types=frozenset({11})).routes} == {
            11
        }


def test_frequency_expansion_is_opt_in_and_expands_exact_times(
    tmp_path: Path, tables: dict[str, str]
) -> None:
    tables["stop_times.txt"] += "B,08:10:00,08:10:00,Q,2\n"
    tables["frequencies.txt"] = (
        "trip_id,start_time,end_time,headway_secs,exact_times\nB,09:00:00,10:00:00,1800,1\n"
    )
    archive = write_archive(tmp_path / "frequency.zip", tables)

    with GTFSFeed.from_file(archive) as feed:
        template = feed.bus()
        expanded = feed.bus(expand_frequencies=True)

    assert [trip.id for trip in template.trips] == ["B"]
    assert [trip.id for trip in expanded.trips] == ["B@32400", "B@34200"]
    assert [
        (item.trip_id, item.arrival_seconds, item.departure_seconds) for item in expanded.stop_times
    ] == [
        ("B@32400", 32400, 32400),
        ("B@32400", 33000, 33000),
        ("B@34200", 34200, 34200),
        ("B@34200", 34800, 34800),
    ]


def test_frequency_headway_templates_remain_unexpanded(
    tmp_path: Path, tables: dict[str, str]
) -> None:
    tables["frequencies.txt"] = (
        "trip_id,start_time,end_time,headway_secs,exact_times\nB,09:00:00,10:00:00,1800,0\n"
    )
    with GTFSFeed.from_file(write_archive(tmp_path / "headway.zip", tables)) as feed:
        network = feed.bus(expand_frequencies=True)

    assert [trip.id for trip in network.trips] == ["B"]


@pytest.mark.parametrize(
    "frequencies, message",
    [
        (
            "trip_id,start_time,end_time,headway_secs,exact_times\nB,10:00:00,09:00:00,1800,1\n",
            "earlier than end_time",
        ),
        (
            "trip_id,start_time,end_time,headway_secs,exact_times\nB,09:00:00,10:00:00,1800,2\n",
            "exact_times",
        ),
        (
            "trip_id,start_time,end_time,headway_secs,exact_times\nB,00:00:00,28:00:00,1,1\n",
            "exceeds 100000",
        ),
    ],
)
def test_frequency_expansion_rejects_invalid_or_excessive_windows(
    tmp_path: Path, tables: dict[str, str], frequencies: str, message: str
) -> None:
    tables["frequencies.txt"] = frequencies
    with GTFSFeed.from_file(write_archive(tmp_path / "bad-frequency.zip", tables)) as feed:
        with pytest.raises(InvalidGTFSFeedError, match=message):
            feed.bus(expand_frequencies=True)


@pytest.mark.parametrize("payload", [b"not a zip", b"", b"PK truncated"])
def test_invalid_zip(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "invalid.zip"
    path.write_bytes(payload)
    with pytest.raises(InvalidGTFSFeedError):
        GTFSFeed.from_file(path)


@pytest.mark.parametrize(
    "replacement",
    [
        "route_id,route_id\nR,R\n",
        "route_id\nR\n",
        "route_id,route_type\nR,1,extra\n",
        "route_id,route_type\nR\n",
    ],
)
def test_invalid_csv(tmp_path: Path, tables: dict[str, str], replacement: str) -> None:
    tables["routes.txt"] = replacement
    with pytest.raises(InvalidGTFSFeedError):
        GTFSFeed.from_file(write_archive(tmp_path / "invalid.zip", tables))


def test_wrapper_and_bom(tmp_path: Path, tables: dict[str, str]) -> None:
    wrapped = {f"feed/{name}": "\ufeff" + value for name, value in tables.items()}
    with GTFSFeed.from_file(write_archive(tmp_path / "wrapped.zip", wrapped)) as feed:
        assert len(list(feed.rows("stops.txt"))) == 5


@pytest.mark.parametrize("extra", ["../stops.txt", "/stops.txt", "wrapper/stops.txt"])
def test_unsafe_or_duplicate_tables(tmp_path: Path, tables: dict[str, str], extra: str) -> None:
    tables[extra] = tables["stops.txt"]
    with pytest.raises(InvalidGTFSFeedError):
        GTFSFeed.from_file(write_archive(tmp_path / "invalid.zip", tables))


def test_archive_changed(archive_path: Path) -> None:
    feed = GTFSFeed.from_file(archive_path)
    archive_path.write_bytes(b"replaced")
    with pytest.raises(InvalidGTFSFeedError, match="changed"):
        list(feed.rows("stops.txt"))


def test_validation_checks_later_records(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["stop_times.txt"] += "T,25:99:00,26:00:00,Q,3\n"
    with GTFSFeed.from_file(write_archive(tmp_path / "invalid.zip", tables)) as feed:
        report = feed.validate()
        assert not report.valid
        issue = next(issue for issue in report.issues if issue.code == "invalid_service_time")
        assert issue.table == "stop_times.txt"
        assert issue.record_number == 7


def test_validation_reports_values_and_relationships(
    tmp_path: Path, tables: dict[str, str]
) -> None:
    tables["routes.txt"] += "UNKNOWN,M,Invalid,Invalid route,99,\n"
    tables["trips.txt"] += "MISSING,WK,UNKNOWN_TRIP,,MISSING_SHAPE\n"
    tables["stop_times.txt"] += "UNKNOWN_TRIP,06:00:00,06:00:00,MISSING_STOP,1\n"
    tables["stops.txt"] += "ORPHAN,Orphan,-33.0,181.0,0,MISSING_PARENT\n"
    with GTFSFeed.from_file(write_archive(tmp_path / "invalid.zip", tables)) as feed:
        report = feed.validate()

    codes = {issue.code for issue in report.issues}
    assert {
        "invalid_route_type",
        "unknown_reference",
        "coordinate_out_of_range",
    } <= codes
    route_reference = next(
        issue
        for issue in report.issues
        if issue.table == "trips.txt" and "route_id" in issue.message
    )
    assert route_reference.record_number == 5


@pytest.mark.parametrize("route_type", [0, 7, 11, 12, 100, 1799])
def test_validation_accepts_standard_and_extended_route_types(
    tmp_path: Path, tables: dict[str, str], route_type: int
) -> None:
    tables["routes.txt"] = tables["routes.txt"].replace(",3,\n", f",{route_type},\n")
    with GTFSFeed.from_file(write_archive(tmp_path / f"route-{route_type}.zip", tables)) as feed:
        assert feed.validate().valid


def test_validation_reports_common_core_record_errors(
    tmp_path: Path, tables: dict[str, str]
) -> None:
    tables["agency.txt"] += ",Missing,https://example.org,America/Santiago\n"
    tables["routes.txt"] += ",UNKNOWN,,,not-a-number,\n"
    tables["stops.txt"] += "BAD,Stop,-91,invalid,9,MISSING\nPARTIAL,Partial,-33.0,,0,\n"
    tables["trips.txt"] += ",,MISSING,,MISSING_SHAPE\n"
    tables["stop_times.txt"] += ",bad,bad,MISSING,not-a-number\n"
    tables["shapes.txt"] += ",invalid,181,not-a-number\n"
    tables["calendar.txt"] += "WK,2,1,1,1,1,1,1,20261231,20260101\n"
    tables["calendar_dates.txt"] += ",20260231,3\n"
    tables["frequencies.txt"] = (
        "trip_id,start_time,end_time,headway_secs,exact_times\n"
        "MISSING,08:00:00,07:00:00,0,2\n"
        "MISSING,,,,\n"
    )
    tables["pathways.txt"] = (
        "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional\nP,MISSING,MISSING,1,0\n"
    )
    tables["transfers.txt"] = "from_stop_id,to_stop_id,transfer_type\nMISSING,MISSING,0\n"
    tables["levels.txt"] = "level_id,level_index\n,bad\nL,inf\n"

    with GTFSFeed.from_file(write_archive(tmp_path / "core-errors.zip", tables)) as feed:
        report = feed.validate()

    codes = {issue.code for issue in report.issues}
    assert {
        "missing_agency_id",
        "missing_required_value",
        "invalid_integer",
        "missing_route_name",
        "unknown_reference",
        "invalid_location_type",
        "incomplete_coordinates",
        "invalid_coordinate",
        "coordinate_out_of_range",
        "invalid_service_time",
        "invalid_weekday_flag",
        "invalid_date",
        "invalid_date_range",
        "invalid_exception_type",
        "invalid_frequency_range",
        "integer_below_minimum",
        "invalid_exact_times",
        "missing_frequency_time",
        "invalid_level_index",
    } <= codes


def test_validation_reports_empty_required_agency_table(
    tmp_path: Path, tables: dict[str, str]
) -> None:
    tables["agency.txt"] = "agency_id,agency_name,agency_url,agency_timezone\n"
    with GTFSFeed.from_file(write_archive(tmp_path / "empty-agency.zip", tables)) as feed:
        report = feed.validate()

    assert "empty_required_table" in {issue.code for issue in report.issues}


def test_validation_bounds_diagnostics(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["routes.txt"] += "R,M,Duplicate,Duplicate route,99,\n" * 505
    with GTFSFeed.from_file(write_archive(tmp_path / "many-issues.zip", tables)) as feed:
        report = feed.validate()

    assert len(report.issues) == 1000
    assert report.diagnostics_truncated


def test_validation_scans_large_stop_times_table(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["stop_times.txt"] += "".join(
        f"B,08:00:00,08:00:00,B,{sequence}\n" for sequence in range(2, 3002)
    )
    with GTFSFeed.from_file(write_archive(tmp_path / "large-feed.zip", tables)) as feed:
        report = feed.validate()

    assert report.valid
    assert report.row_counts["stop_times.txt"] == 3005


@pytest.mark.parametrize(
    "value,expected", [("25:10:00", 90600), ("0:00:00", 0), ("24:00:00", 86400)]
)
def test_service_times(value: str, expected: int) -> None:
    assert parse_service_time(value) == expected


@pytest.mark.parametrize("value", ["-1:00:00", "24:60:00", "00:00:60", "bad", ""])
def test_invalid_service_times(value: str) -> None:
    with pytest.raises(InvalidGTFSFeedError):
        parse_service_time(value)


def test_relative_path_survives_working_directory_change(
    tmp_path: Path,
    archive_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(archive_path.parent)
    with GTFSFeed.from_file(archive_path.name) as feed:
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)
        assert len(list(feed.rows("routes.txt"))) == 2
