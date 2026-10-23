"""Measure validation time on a generated feed with a configurable stop_times size."""

import argparse
import csv
import json
import time
from collections.abc import Iterable, Sequence
from io import TextIOWrapper
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from chile_dtpm_gtfs import GTFSFeed


def write_table(archive: ZipFile, name: str, rows: Iterable[Sequence[str]]) -> None:
    """Write generated CSV rows directly into a ZIP member."""
    with archive.open(name, "w") as member:
        with TextIOWrapper(member, encoding="utf-8", newline="") as text:
            csv.writer(text).writerows(rows)


def build_feed(path: Path, stop_time_count: int) -> None:
    """Create a minimal, valid feed without materializing its large table."""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        write_table(
            archive,
            "agency.txt",
            [
                ("agency_id", "agency_name", "agency_url", "agency_timezone"),
                ("A", "Benchmark", "https://example.org", "America/Santiago"),
            ],
        )
        write_table(
            archive,
            "stops.txt",
            [
                ("stop_id", "stop_name", "stop_lat", "stop_lon"),
                ("S", "Benchmark stop", "-33.45", "-70.65"),
            ],
        )
        write_table(
            archive,
            "routes.txt",
            [
                ("route_id", "agency_id", "route_short_name", "route_type"),
                ("R", "A", "1", "1"),
            ],
        )
        write_table(
            archive,
            "trips.txt",
            [
                ("route_id", "service_id", "trip_id"),
                ("R", "WK", "T"),
            ],
        )
        write_table(
            archive,
            "stop_times.txt",
            chain(
                [
                    (
                        "trip_id",
                        "arrival_time",
                        "departure_time",
                        "stop_id",
                        "stop_sequence",
                    )
                ],
                (
                    ("T", "08:00:00", "08:00:00", "S", str(sequence))
                    for sequence in range(1, stop_time_count + 1)
                ),
            ),
        )
        write_table(
            archive,
            "calendar.txt",
            [
                (
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
                ),
                ("WK", "1", "1", "1", "1", "1", "1", "1", "20260101", "20261231"),
            ],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-times", type=int, default=100_000)
    arguments = parser.parse_args()
    if arguments.stop_times < 1:
        parser.error("--stop-times must be greater than zero.")

    with TemporaryDirectory(prefix="chile-dtpm-gtfs-benchmark-") as directory:
        path = Path(directory) / "benchmark.zip"
        build_feed(path, arguments.stop_times)
        archive_bytes = path.stat().st_size
        with GTFSFeed.from_file(path) as feed:
            started = time.perf_counter()
            report = feed.validate()
            elapsed = time.perf_counter() - started

    print(
        json.dumps(
            {
                "stop_times": arguments.stop_times,
                "archive_bytes": archive_bytes,
                "validation_seconds": round(elapsed, 6),
                "valid": report.valid,
                "diagnostic_count": len(report.issues),
                "diagnostics_truncated": report.diagnostics_truncated,
            },
            indent=2,
        )
    )
    if not report.valid:
        raise SystemExit("Generated benchmark feed failed validation.")


if __name__ == "__main__":
    main()
