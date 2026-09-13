"""Bounded ZIP access and streaming CSV decoding without extraction."""

import csv
from collections.abc import Generator
from io import TextIOWrapper
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "agency.txt": {"agency_name", "agency_url", "agency_timezone"},
    "stops.txt": {"stop_id"},
    "routes.txt": {"route_id", "route_type"},
    "trips.txt": {"route_id", "service_id", "trip_id"},
    "stop_times.txt": {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"},
}
OPTIONAL_COLUMNS: dict[str, set[str]] = {
    "calendar.txt": {
        "service_id",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "start_date",
        "end_date",
    },
    "calendar_dates.txt": {"service_id", "date", "exception_type"},
    "shapes.txt": {"shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"},
    "feed_info.txt": {"feed_publisher_name", "feed_publisher_url", "feed_lang"},
    "transfers.txt": {"transfer_type"},
    "pathways.txt": {
        "pathway_id",
        "from_stop_id",
        "to_stop_id",
        "pathway_mode",
        "is_bidirectional",
    },
    "levels.txt": {"level_id", "level_index"},
    "frequencies.txt": {"trip_id", "start_time", "end_time", "headway_secs"},
}
ZIP_ERRORS = (
    BadZipFile,
    OSError,
    UnicodeError,
    csv.Error,
    RuntimeError,
    NotImplementedError,
    EOFError,
)


class GTFSLoader:
    """Read UTF-8 CSV tables from one ZIP while guarding archive structure."""

    def __init__(self, path: str | Path, *, max_uncompressed_bytes: int = 8 * 1024**3) -> None:
        """Index root tables or tables under one common wrapper directory."""
        self.path = Path(path)
        self.members: dict[str, str] = {}
        try:
            with ZipFile(self.path) as archive:
                entries = archive.infolist()
                if (
                    len(entries) > 1000
                    or sum(item.file_size for item in entries) > max_uncompressed_bytes
                ):
                    raise InvalidGTFSFeedError(
                        "ZIP exceeds member count or uncompressed size limit."
                    )
                roots: set[str] = set()
                for item in entries:
                    name = PurePosixPath(item.filename)
                    if name.is_absolute() or ".." in name.parts or "\\" in item.filename:
                        raise InvalidGTFSFeedError(f"Unsafe archive member: {item.filename!r}")
                    if item.is_dir() or not item.filename.endswith(".txt"):
                        continue
                    if name.name in self.members:
                        raise InvalidGTFSFeedError(f"Duplicate GTFS table: {name.name}")
                    roots.add(str(name.parent))
                    self.members[name.name] = item.filename
                if len(roots) > 1:
                    raise InvalidGTFSFeedError("GTFS tables must share one archive directory.")
                missing = REQUIRED_COLUMNS.keys() - self.members.keys()
                if missing:
                    raise InvalidGTFSFeedError(
                        f"Missing required GTFS files: {', '.join(sorted(missing))}"
                    )
            self._signature = self._stat()
            for table in self.members:
                iterator = self.rows(table)
                try:
                    next(iterator, None)
                finally:
                    iterator.close()
        except ZIP_ERRORS as exc:
            raise InvalidGTFSFeedError(f"Unable to load GTFS archive {self.path}: {exc}") from exc

    def _stat(self) -> tuple[int, int]:
        info = self.path.stat()
        return info.st_size, info.st_mtime_ns

    def rows(self, table: str) -> Generator[dict[str, str]]:
        """Yield raw string records; absent optional tables yield no records.

        Every row must match its header width. Required headers and unique column
        names are checked even for header-only tables. Files are not extracted.
        """
        if table not in self.members:
            return
        try:
            if self._stat() != self._signature:
                raise InvalidGTFSFeedError("The archive changed after loading; reopen the feed.")
            with ZipFile(self.path) as archive, archive.open(self.members[table]) as raw:
                with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                    reader = csv.reader(text, strict=True)
                    header = next(reader, [])
                    if (
                        not header
                        or any(not name for name in header)
                        or len(header) != len(set(header))
                    ):
                        raise InvalidGTFSFeedError(f"Invalid or duplicate CSV headers in {table}")
                    required = REQUIRED_COLUMNS.get(table, OPTIONAL_COLUMNS.get(table, set()))
                    missing = required - set(header)
                    if missing:
                        raise InvalidGTFSFeedError(
                            f"Missing columns in {table}: {', '.join(sorted(missing))}"
                        )
                    for row in reader:
                        if not row:
                            continue
                        if len(row) != len(header):
                            raise InvalidGTFSFeedError(
                                f"Invalid column count in {table}, line {reader.line_num}"
                            )
                        yield dict(zip(header, row, strict=True))
        except ZIP_ERRORS as exc:
            raise InvalidGTFSFeedError(f"Unable to read {table}: {exc}") from exc
