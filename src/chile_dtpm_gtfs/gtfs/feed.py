"""Public local and remote GTFS feed access with explicit resource ownership."""

import hashlib
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date
from itertools import islice
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chile_dtpm_gtfs.domain.network import TransitNetwork

import httpx

from chile_dtpm_gtfs.exceptions import InvalidGTFSFeedError
from chile_dtpm_gtfs.gtfs.loader import GTFSLoader
from chile_dtpm_gtfs.gtfs.metadata import FeedMetadata
from chile_dtpm_gtfs.gtfs.validator import GTFSValidator, ValidationReport
from chile_dtpm_gtfs.source.downloader import FeedDownloader


def parse_feed_date(value: str) -> date | None:
    """Parse an optional YYYYMMDD date with a library-specific error."""
    if not value:
        return None
    try:
        if len(value) != 8 or not value.isascii() or not value.isdigit():
            raise ValueError("expected YYYYMMDD")
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError as exc:
        raise InvalidGTFSFeedError(f"Invalid GTFS date: {value!r}") from exc


class GTFSFeed:
    """An archive-backed feed. Keep local files unchanged while the feed is open."""

    def __init__(self, loader: GTFSLoader, metadata: FeedMetadata) -> None:
        """Use from_file/from_url for normal construction."""
        self._loader = loader
        self.metadata = metadata
        self._temporary: TemporaryDirectory[str] | None = None
        self._closed = False

    @classmethod
    def from_file(cls, path: str | Path) -> "GTFSFeed":
        """Check archive structure and metadata, hashing bytes without network access."""
        loader = GTFSLoader(path)
        try:
            with loader.path.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
        except OSError as exc:
            raise InvalidGTFSFeedError(f"Unable to hash archive: {exc}") from exc
        metadata = FeedMetadata(
            sha256=digest,
            original_filename=loader.path.name,
            size_bytes=loader.path.stat().st_size,
        )
        with closing(loader.rows("feed_info.txt")) as records:
            info = list(islice(records, 2))
        if len(info) > 1:
            raise InvalidGTFSFeedError("feed_info.txt must contain at most one record.")
        if info:
            row = info[0]
            metadata = replace(
                metadata,
                feed_start_date=parse_feed_date(row.get("feed_start_date", "")),
                feed_end_date=parse_feed_date(row.get("feed_end_date", "")),
                feed_version=row.get("feed_version") or None,
            )
            if (
                metadata.feed_start_date
                and metadata.feed_end_date
                and metadata.feed_start_date > metadata.feed_end_date
            ):
                raise InvalidGTFSFeedError("feed_info start date is after end date.")
        return cls(loader, metadata)

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        destination: str | Path | None = None,
        timeout: float = 60.0,
        max_bytes: int = 2 * 1024**3,
        transport: httpx.BaseTransport | None = None,
    ) -> "GTFSFeed":
        """Download and load a feed, owning temporary storage when no destination is given.

        Existing destinations are never replaced. Explicit downloads remain on
        disk after close; temporary archives are removed on close/context exit.
        """
        temporary = TemporaryDirectory(prefix="chile-dtpm-gtfs-") if destination is None else None
        path = Path(temporary.name) / "feed.zip" if temporary else Path(destination or "feed.zip")
        try:
            result = FeedDownloader(
                timeout=timeout, max_bytes=max_bytes, transport=transport
            ).download(url, path)
            feed = cls.from_file(result.path)
            feed.metadata = replace(
                feed.metadata,
                source_url=result.source_url,
                resolved_url=result.resolved_url,
                original_filename=result.filename,
                downloaded_at=result.downloaded_at,
                content_length=result.content_length,
            )
            feed._temporary = temporary
            return feed
        except Exception:
            if temporary is not None:
                temporary.cleanup()
            raise

    @property
    def path(self) -> Path:
        """Archive path; temporary paths are valid only while this feed is open."""
        return self._loader.path

    @property
    def tables(self) -> tuple[str, ...]:
        """Names of all available GTFS text tables, including extensions."""
        return tuple(sorted(self._loader.members))

    def rows(self, table: str) -> Iterator[dict[str, str]]:
        """Stream raw string rows; optional absent tables are empty."""
        self._ensure_open()
        yield from self._loader.rows(table)

    def validate(self) -> ValidationReport:
        """Read all records for basic CSV, integrity, and service-time validation."""
        self._ensure_open()
        return GTFSValidator().validate(self._loader)

    def select(self, *, route_types: frozenset[int], on: date | None = None) -> "TransitNetwork":
        """Select route types through GTFS relationships into an independent snapshot."""
        from chile_dtpm_gtfs.selectors.metro import select_network

        self._ensure_open()
        return select_network(self, route_types=route_types, on=on)

    def metro(self, *, on: date | None = None) -> "TransitNetwork":
        """Select subway routes (route_type=1), optionally filtering a service date."""
        return self.select(route_types=frozenset({1}), on=on)

    def _ensure_open(self) -> None:
        if self._closed:
            raise InvalidGTFSFeedError("The feed is closed.")

    def close(self) -> None:
        """Release owned temporary storage; never delete a caller-owned archive."""
        if self._temporary is not None:
            self._temporary.cleanup()
        self._closed = True

    def __enter__(self) -> "GTFSFeed":
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
