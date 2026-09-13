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
        assert feed.validate().row_counts["stop_times.txt"] == 5
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
        with pytest.raises(InvalidGTFSFeedError, match="service time"):
            feed.validate()


@pytest.mark.parametrize(
    "value,expected", [("25:10:00", 90600), ("0:00:00", 0), ("24:00:00", 86400)]
)
def test_service_times(value: str, expected: int) -> None:
    assert parse_service_time(value) == expected


@pytest.mark.parametrize("value", ["-1:00:00", "24:60:00", "00:00:60", "bad", ""])
def test_invalid_service_times(value: str) -> None:
    with pytest.raises(InvalidGTFSFeedError):
        parse_service_time(value)
