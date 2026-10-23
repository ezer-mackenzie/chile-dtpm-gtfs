"""Basic archive validation with actionable core GTFS diagnostics."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError
from chile_dtpm_gtfs.gtfs.loader import GTFSLoader
from chile_dtpm_gtfs.gtfs.time import parse_service_time

MAX_DIAGNOSTICS = 1000
ROUTE_TYPES = frozenset({*range(8), 11, 12})


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One error located in a logical CSV record; the header is record 1."""

    code: str
    table: str
    record_number: int
    message: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Record counts and bounded semantic diagnostics from a full feed scan."""

    row_counts: dict[str, int]
    issues: tuple[ValidationIssue, ...]
    diagnostics_truncated: bool

    @property
    def valid(self) -> bool:
        """Whether no validation errors were found."""
        return not self.issues


class GTFSValidator:
    """Validate CSV integrity, supported service times, core values, and references."""

    def validate(self, loader: GTFSLoader) -> ValidationReport:
        """Read every table and report common core GTFS errors without stopping early."""
        counts: dict[str, int] = {}
        issues: list[ValidationIssue] = []
        diagnostics_truncated = False
        known_ids: dict[str, set[str]] = {
            name: set() for name in ("agency", "route", "stop", "trip", "shape", "service", "level")
        }
        calendar_service_ids: set[str] = set()
        agency_count = 0

        def add_issue(code: str, table: str, record_number: int, message: str) -> None:
            nonlocal diagnostics_truncated
            if len(issues) < MAX_DIAGNOSTICS:
                issues.append(ValidationIssue(code, table, record_number, message))
            else:
                diagnostics_truncated = True

        def integer(
            value: str, *, table: str, record: int, field: str, minimum: int = 0
        ) -> int | None:
            if not value.isascii() or not value.isdigit():
                add_issue(
                    "invalid_integer", table, record, f"{field} must be an integer; got {value!r}."
                )
                return None
            parsed = int(value)
            if parsed < minimum:
                add_issue(
                    "integer_below_minimum",
                    table,
                    record,
                    f"{field} must be at least {minimum}; got {parsed}.",
                )
                return None
            return parsed

        def gtfs_date(value: str, *, table: str, record: int, field: str) -> date | None:
            if len(value) != 8 or not value.isascii() or not value.isdigit():
                add_issue(
                    "invalid_date", table, record, f"{field} must use YYYYMMDD; got {value!r}."
                )
                return None
            try:
                return date(int(value[:4]), int(value[4:6]), int(value[6:]))
            except ValueError:
                add_issue("invalid_date", table, record, f"{field} is not a calendar date.")
                return None

        id_columns = {
            "agency.txt": ("agency", "agency_id"),
            "routes.txt": ("route", "route_id"),
            "stops.txt": ("stop", "stop_id"),
            "trips.txt": ("trip", "trip_id"),
            "calendar.txt": ("service", "service_id"),
        }

        for table in loader.members:
            for count, row in enumerate(loader.rows(table), start=1):
                identifier_spec = id_columns.get(table)
                if identifier_spec is not None:
                    id_kind, column = identifier_spec
                    identifier = row.get(column, "")
                    if identifier:
                        seen = (
                            calendar_service_ids if table == "calendar.txt" else known_ids[id_kind]
                        )
                        if identifier in seen:
                            add_issue(
                                "duplicate_identifier",
                                table,
                                count + 1,
                                f"{column} {identifier!r} is duplicated.",
                            )
                        seen.add(identifier)
                        known_ids[id_kind].add(identifier)
                if table == "agency.txt":
                    agency_count += 1
                elif table == "shapes.txt" and row.get("shape_id"):
                    known_ids["shape"].add(row["shape_id"])
                elif table == "calendar_dates.txt" and row.get("service_id"):
                    known_ids["service"].add(row["service_id"])
                elif table == "levels.txt" and row.get("level_id"):
                    known_ids["level"].add(row["level_id"])

        if agency_count == 0:
            add_issue("empty_required_table", "agency.txt", 1, "agency.txt must contain a record.")

        for table in loader.members:
            count = 0
            for row in loader.rows(table):
                count += 1
                record = count + 1

                if table == "agency.txt":
                    if agency_count > 1 and not row.get("agency_id", ""):
                        add_issue(
                            "missing_agency_id",
                            table,
                            record,
                            "agency_id is required when the feed contains multiple agencies.",
                        )
                    for field in ("agency_name", "agency_url", "agency_timezone"):
                        if not row.get(field, ""):
                            add_issue(
                                "missing_required_value",
                                table,
                                record,
                                f"{field} must not be empty.",
                            )

                elif table == "routes.txt":
                    if not row.get("route_id", ""):
                        add_issue(
                            "missing_required_value",
                            table,
                            record,
                            "route_id must not be empty.",
                        )
                    route_type = integer(
                        row.get("route_type", ""),
                        table=table,
                        record=record,
                        field="route_type",
                    )
                    if route_type is not None and not self._valid_route_type(route_type):
                        add_issue(
                            "invalid_route_type",
                            table,
                            record,
                            f"route_type is not a standard or extended GTFS type: {route_type}.",
                        )
                    if not row.get("route_short_name") and not row.get("route_long_name"):
                        add_issue(
                            "missing_route_name",
                            table,
                            record,
                            "At least one of route_short_name or route_long_name is required.",
                        )
                    self._check_reference(
                        known_ids,
                        row,
                        table,
                        record,
                        "agency_id",
                        "agency",
                        add_issue,
                    )

                elif table == "stops.txt":
                    if not row.get("stop_id", ""):
                        add_issue(
                            "missing_required_value",
                            table,
                            record,
                            "stop_id must not be empty.",
                        )
                    location_type = integer(
                        row.get("location_type") or "0",
                        table=table,
                        record=record,
                        field="location_type",
                    )
                    if location_type is not None and location_type not in range(5):
                        add_issue(
                            "invalid_location_type",
                            table,
                            record,
                            f"location_type must be between 0 and 4; got {location_type}.",
                        )
                    latitude, longitude = row.get("stop_lat", ""), row.get("stop_lon", "")
                    if bool(latitude) != bool(longitude):
                        add_issue(
                            "incomplete_coordinates",
                            table,
                            record,
                            "stop_lat and stop_lon must either both be set or both be empty.",
                        )
                    elif latitude and longitude:
                        self._coordinate(latitude, -90, 90, "stop_lat", table, record, add_issue)
                        self._coordinate(longitude, -180, 180, "stop_lon", table, record, add_issue)
                    self._check_reference(
                        known_ids,
                        row,
                        table,
                        record,
                        "parent_station",
                        "stop",
                        add_issue,
                    )
                    self._check_reference(
                        known_ids,
                        row,
                        table,
                        record,
                        "level_id",
                        "level",
                        add_issue,
                    )

                elif table == "trips.txt":
                    if not row.get("trip_id", ""):
                        add_issue(
                            "missing_required_value",
                            table,
                            record,
                            "trip_id must not be empty.",
                        )
                    for field in ("route_id", "service_id"):
                        if not row.get(field, ""):
                            add_issue(
                                "missing_required_value",
                                table,
                                record,
                                f"{field} must not be empty.",
                            )
                    for field, target in (
                        ("route_id", "route"),
                        ("service_id", "service"),
                        ("shape_id", "shape"),
                    ):
                        self._check_reference(
                            known_ids,
                            row,
                            table,
                            record,
                            field,
                            target,
                            add_issue,
                        )

                elif table == "stop_times.txt":
                    for field in ("trip_id", "stop_id", "stop_sequence"):
                        if not row.get(field, ""):
                            add_issue(
                                "missing_required_value",
                                table,
                                record,
                                f"{field} must not be empty.",
                            )
                    for field, target in (("trip_id", "trip"), ("stop_id", "stop")):
                        self._check_reference(
                            known_ids,
                            row,
                            table,
                            record,
                            field,
                            target,
                            add_issue,
                        )
                    sequence = row.get("stop_sequence", "")
                    if sequence:
                        integer(sequence, table=table, record=record, field="stop_sequence")
                    if not row.get("arrival_time") and not row.get("departure_time"):
                        add_issue(
                            "missing_stop_time",
                            table,
                            record,
                            "At least one of arrival_time or departure_time is required.",
                        )
                    for field in ("arrival_time", "departure_time"):
                        value = row.get(field, "")
                        if value:
                            try:
                                parse_service_time(value)
                            except InvalidGTFSFeedError as exc:
                                add_issue("invalid_service_time", table, record, str(exc))

                elif table == "shapes.txt":
                    identifier = row.get("shape_id", "")
                    if not identifier:
                        add_issue(
                            "missing_required_value",
                            table,
                            record,
                            "shape_id must not be empty.",
                        )
                    for field, minimum, maximum in (
                        ("shape_pt_lat", -90, 90),
                        ("shape_pt_lon", -180, 180),
                    ):
                        self._coordinate(
                            row.get(field, ""), minimum, maximum, field, table, record, add_issue
                        )
                    integer(
                        row.get("shape_pt_sequence", ""),
                        table=table,
                        record=record,
                        field="shape_pt_sequence",
                    )

                elif table == "calendar.txt":
                    if not row.get("service_id", ""):
                        add_issue(
                            "missing_required_value",
                            table,
                            record,
                            "service_id must not be empty.",
                        )
                    for field in (
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ):
                        if row.get(field) not in {"0", "1"}:
                            add_issue(
                                "invalid_weekday_flag",
                                table,
                                record,
                                f"{field} must be 0 or 1; got {row.get(field)!r}.",
                            )
                    start = gtfs_date(
                        row.get("start_date", ""),
                        table=table,
                        record=record,
                        field="start_date",
                    )
                    end = gtfs_date(
                        row.get("end_date", ""),
                        table=table,
                        record=record,
                        field="end_date",
                    )
                    if start is not None and end is not None and start > end:
                        add_issue(
                            "invalid_date_range",
                            table,
                            record,
                            "start_date must not be later than end_date.",
                        )

                elif table == "calendar_dates.txt":
                    service_id = row.get("service_id", "")
                    if not service_id:
                        add_issue(
                            "missing_required_value",
                            table,
                            record,
                            "service_id must not be empty.",
                        )
                    gtfs_date(row.get("date", ""), table=table, record=record, field="date")
                    if row.get("exception_type") not in {"1", "2"}:
                        add_issue(
                            "invalid_exception_type",
                            table,
                            record,
                            "exception_type must be 1 or 2.",
                        )

                elif table == "frequencies.txt":
                    self._check_reference(
                        known_ids, row, table, record, "trip_id", "trip", add_issue
                    )
                    frequency_times: dict[str, int] = {}
                    for field in ("start_time", "end_time"):
                        value = row.get(field, "")
                        if value:
                            try:
                                frequency_times[field] = parse_service_time(value)
                            except InvalidGTFSFeedError as exc:
                                add_issue("invalid_service_time", table, record, str(exc))
                    if (
                        "start_time" in frequency_times
                        and "end_time" in frequency_times
                        and frequency_times["start_time"] >= frequency_times["end_time"]
                    ):
                        add_issue(
                            "invalid_frequency_range",
                            table,
                            record,
                            "start_time must be earlier than end_time.",
                        )
                    integer(
                        row.get("headway_secs", ""),
                        table=table,
                        record=record,
                        field="headway_secs",
                        minimum=1,
                    )
                    exact = row.get("exact_times", "")
                    if exact and exact not in {"0", "1"}:
                        add_issue(
                            "invalid_exact_times",
                            table,
                            record,
                            "exact_times must be 0, 1, or empty.",
                        )
                    if not row.get("start_time") or not row.get("end_time"):
                        add_issue(
                            "missing_frequency_time",
                            table,
                            record,
                            "start_time and end_time are required when headway_secs is set.",
                        )

                elif table in {"pathways.txt", "transfers.txt"}:
                    for field in ("from_stop_id", "to_stop_id"):
                        self._check_reference(
                            known_ids,
                            row,
                            table,
                            record,
                            field,
                            "stop",
                            add_issue,
                        )

                elif table == "levels.txt":
                    level_id = row.get("level_id", "")
                    if not level_id:
                        add_issue(
                            "missing_required_value",
                            table,
                            record,
                            "level_id must not be empty.",
                        )
                    try:
                        level_index = float(row.get("level_index", ""))
                    except ValueError:
                        add_issue(
                            "invalid_level_index",
                            table,
                            record,
                            "level_index must be numeric.",
                        )
                    else:
                        if not math.isfinite(level_index):
                            add_issue(
                                "invalid_level_index",
                                table,
                                record,
                                "level_index must be finite.",
                            )

                counts[table] = count

        return ValidationReport(counts, tuple(issues), diagnostics_truncated)

    @staticmethod
    def _check_reference(
        known_ids: dict[str, set[str]],
        row: dict[str, str],
        table: str,
        record: int,
        field: str,
        target: str,
        add_issue: Callable[[str, str, int, str], None],
    ) -> None:
        value = row.get(field, "")
        if not value or value in known_ids[target]:
            return
        add_issue(
            "unknown_reference",
            table,
            record,
            f"{field} references unknown {target} identifier {value!r}.",
        )

    @staticmethod
    def _valid_route_type(value: int) -> bool:
        return value in ROUTE_TYPES or 100 <= value <= 1799

    @staticmethod
    def _coordinate(
        value: str,
        minimum: int,
        maximum: int,
        field: str,
        table: str,
        record: int,
        add_issue: Callable[[str, str, int, str], None],
    ) -> None:
        try:
            number = float(value)
        except ValueError:
            add_issue(
                "invalid_coordinate",
                table,
                record,
                f"{field} must be numeric; got {value!r}.",
            )
            return
        if not math.isfinite(number) or not minimum <= number <= maximum:
            add_issue(
                "coordinate_out_of_range",
                table,
                record,
                f"{field} must be between {minimum} and {maximum}; got {value!r}.",
            )
