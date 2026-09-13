"""Locale-independent parsing of Spanish publication dates."""

import re
from datetime import date

from chile_dtpm_gtfs.exceptions import DTPMSourceParseError

MONTHS = dict(
    enumerate(
        (
            "enero febrero marzo abril mayo junio julio agosto "
            "septiembre octubre noviembre diciembre"
        ).split(),
        1,
    )
)
DATE_PATTERN = re.compile(r"(\d{1,2})\s+de\s+([a-z]+)\s+(?:de\s+)?(\d{4})", re.I)


def parse_spanish_date(value: str) -> date:
    """Parse a complete Spanish date, accepting an optional 'de' before the year."""
    match = DATE_PATTERN.fullmatch(value.strip())
    if match:
        day, month_name, year = match.groups()
        months = {name: number for number, name in MONTHS.items()}
        try:
            return date(int(year), months[month_name.lower()], int(day))
        except (KeyError, ValueError):
            pass
    raise DTPMSourceParseError(f"Invalid Spanish publication date: {value!r}")
