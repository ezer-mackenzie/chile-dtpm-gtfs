"""Measure a generated feed's load, validation, selection, and export workflows."""

import argparse
import csv
import json
import time
from collections.abc import Callable, Iterable, Sequence
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


def measure[T](action: Callable[[], T]) -> tuple[T, float]:
    """Run one stage and return its result and elapsed seconds."""
    started = time.perf_counter()
    result = action()
    return result, time.perf_counter() - started


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
        feed, load_seconds = measure(lambda: GTFSFeed.from_file(path))
        try:
            report, validation_seconds = measure(feed.validate)
            network, selection_seconds = measure(lambda: feed.select(route_types=frozenset({1})))
            geojson, geojson_seconds = measure(network.to_geojson)
            normalized_json, normalized_json_seconds = measure(network.to_json)
            geojson_bytes = len(json.dumps(geojson, allow_nan=False))
            normalized_json_bytes = len(json.dumps(normalized_json, allow_nan=False))
        finally:
            feed.close()

    print(
        json.dumps(
            {
                "stop_times": arguments.stop_times,
                "archive_bytes": archive_bytes,
                "load_seconds": round(load_seconds, 6),
                "validation_seconds": round(validation_seconds, 6),
                "selection_seconds": round(selection_seconds, 6),
                "geojson_seconds": round(geojson_seconds, 6),
                "normalized_json_seconds": round(normalized_json_seconds, 6),
                "geojson_bytes": geojson_bytes,
                "normalized_json_bytes": normalized_json_bytes,
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
