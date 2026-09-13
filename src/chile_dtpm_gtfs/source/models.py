"""Publication metadata, independent of feed contents."""

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from chile_dtpm_gtfs.gtfs.feed import GTFSFeed

SOURCE_URL = "https://www.dtpm.cl/index.php/gtfs-vigente"


@dataclass(frozen=True, slots=True)
class FeedPublication:
    """An advertised feed; dates describe publication applicability, not GTFS coverage."""

    title: str
    effective_from: date
    download_url: str
    filename: str
    description: str | None = None

    source_page: str = SOURCE_URL

    def download(
        self,
        *,
        destination: str | Path | None = None,
        timeout: float = 60.0,
        max_bytes: int = 2 * 1024**3,
        transport: httpx.BaseTransport | None = None,
    ) -> "GTFSFeed":
        """Explicitly download a feed and attach publication provenance."""
        from chile_dtpm_gtfs.gtfs.feed import GTFSFeed

        feed = GTFSFeed.from_url(
            self.download_url,
            destination=destination,
            timeout=timeout,
            max_bytes=max_bytes,
            transport=transport,
        )
        feed.metadata = replace(
            feed.metadata,
            source_page=self.source_page,
            published_effective_from=self.effective_from,
            original_filename=self.filename,
        )
        return feed
