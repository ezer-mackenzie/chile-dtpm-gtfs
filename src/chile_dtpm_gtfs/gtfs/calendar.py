"""Calendar normalization and exception semantics."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date

from chile_dtpm_gtfs.domain.models import Service, ServiceException
from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError
from chile_dtpm_gtfs.gtfs.feed import parse_feed_date
from chile_dtpm_gtfs.gtfs.normalize import required

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def services(
    identifiers: set[str],
    calendar: Iterable[dict[str, str]],
    exceptions: Iterable[dict[str, str]],
) -> tuple[Service, ...]:
    """Build service calendars, allowing exception-only and unknown services."""
    weekly: dict[str, tuple[date, date, tuple[bool, ...]]] = {}
    changes: dict[str, dict[date, ServiceException]] = defaultdict(dict)
    for row in calendar:
        identifier = required(row, "service_id")
        if identifier not in identifiers:
            continue
        if identifier in weekly:
            raise InvalidGTFSFeedError(f"Duplicate calendar service: {identifier!r}")
        start = parse_feed_date(required(row, "start_date"))
        end = parse_feed_date(required(row, "end_date"))
        if start is None or end is None or start > end:
            raise InvalidGTFSFeedError(f"Invalid calendar date range for {identifier!r}")
        values = tuple(required(row, day) for day in DAYS)
        if any(value not in {"0", "1"} for value in values):
            raise InvalidGTFSFeedError(f"Invalid calendar weekday for {identifier!r}")
        weekly[identifier] = start, end, tuple(value == "1" for value in values)
    for row in exceptions:
        identifier = required(row, "service_id")
        if identifier not in identifiers:
            continue
        on = parse_feed_date(required(row, "date"))
        kind = required(row, "exception_type")
        if on is None or kind not in {"1", "2"}:
            raise InvalidGTFSFeedError(f"Invalid calendar exception for {identifier!r}")
        if on in changes[identifier]:
            raise InvalidGTFSFeedError(f"Duplicate calendar exception for {identifier!r} on {on}")
        changes[identifier][on] = ServiceException(on, kind == "1")
    result = []
    for identifier in sorted(identifiers):
        record = weekly.get(identifier)
        result.append(
            Service(
                identifier,
                record[0] if record else None,
                record[1] if record else None,
                record[2] if record else (),
                tuple(changes[identifier][on] for on in sorted(changes[identifier])),
            )
        )
    return tuple(result)
