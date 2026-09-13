"""Metadata that separates publication dates from internal feed coverage."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class FeedMetadata:
    """Provenance for an archive and optional feed_info coverage/version fields."""

    sha256: str
    original_filename: str
    size_bytes: int
    source_url: str | None = None
    resolved_url: str | None = None
    source_page: str | None = None
    published_effective_from: date | None = None
    downloaded_at: datetime | None = None
    content_length: int | None = None
    feed_start_date: date | None = None
    feed_end_date: date | None = None
    feed_version: str | None = None
