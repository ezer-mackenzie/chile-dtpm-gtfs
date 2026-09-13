"""Basic archive validation; not a complete GTFS specification validator."""

from dataclasses import dataclass

from chile_dtpm_gtfs.gtfs.loader import GTFSLoader
from chile_dtpm_gtfs.gtfs.time import parse_service_time


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Record counts for successfully decoded tables."""

    row_counts: dict[str, int]


class GTFSValidator:
    """Validate complete CSV streams and supported time values."""

    def validate(self, loader: GTFSLoader) -> ValidationReport:
        """Read every table fully, including ZIP CRC checks performed by zipfile."""
        counts: dict[str, int] = {}
        for name in loader.members:
            count = 0
            for row in loader.rows(name):
                if name in {"stop_times.txt", "frequencies.txt"}:
                    for column in ("arrival_time", "departure_time", "start_time", "end_time"):
                        value = row.get(column, "")
                        if value:
                            parse_service_time(value)
                count += 1
            counts[name] = count
        return ValidationReport(counts)
