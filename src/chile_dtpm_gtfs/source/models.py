"""Publication metadata, independent of feed contents."""

from dataclasses import dataclass
from datetime import date

SOURCE_URL = "https://www.dtpm.cl/index.php/gtfs-vigente"


@dataclass(frozen=True, slots=True)
class FeedPublication:
    """An advertised feed; dates describe publication applicability, not GTFS coverage."""

    title: str
    effective_from: date
    download_url: str
    filename: str
    description: str | None = None
