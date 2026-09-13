"""GTFS service times, including hours beyond midnight."""

import re

from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError


def parse_service_time(value: str) -> int:
    """Return seconds from service-day start; blank times must be handled by callers."""
    if not re.fullmatch(r"\d{1,3}:[0-5]\d:[0-5]\d", value):
        raise InvalidGTFSFeedError(f"Invalid GTFS service time: {value!r}")
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    return hours * 3600 + minutes * 60 + seconds
