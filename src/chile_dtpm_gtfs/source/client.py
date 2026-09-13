"""HTTP retrieval and the public discovery facade."""

from datetime import date

import httpx

from chile_dtpm_gtfs.exceptions import DTPMSourceError
from chile_dtpm_gtfs.source.models import SOURCE_URL, FeedPublication
from chile_dtpm_gtfs.source.parser import PublicationParser
from chile_dtpm_gtfs.source.resolver import CurrentFeedResolver


class DTPMWebsiteClient:
    """Fetch the official index with bounded requests and explicit HTTP errors."""

    def __init__(
        self, *, timeout: float = 30.0, transport: httpx.BaseTransport | None = None
    ) -> None:
        """Configure request timeout and an optional transport for offline testing."""
        self.timeout = timeout
        self.transport = transport

    def fetch(self) -> tuple[str, str]:
        """Return HTML and the final page URL, following redirects."""
        try:
            with httpx.Client(
                timeout=self.timeout, follow_redirects=True, transport=self.transport
            ) as client:
                response = client.get(SOURCE_URL)
                response.raise_for_status()
                return response.text, str(response.url)
        except httpx.HTTPError as exc:
            raise DTPMSourceError(f"Unable to retrieve DTPM publications: {exc}") from exc


class DTPM:
    """Discover publication metadata without downloading GTFS archives."""

    def __init__(
        self, *, timeout: float = 30.0, transport: httpx.BaseTransport | None = None
    ) -> None:
        """Configure discovery; construction performs no network requests."""
        self._client = DTPMWebsiteClient(timeout=timeout, transport=transport)

    def publications(self) -> list[FeedPublication]:
        """Fetch all advertised publications in page order; no cache is used."""
        html, source_url = self._client.fetch()
        return PublicationParser().parse(html, source_url=source_url)

    def current(self, *, on: date | None = None) -> FeedPublication:
        """Fetch and resolve the applicable publication, excluding future dates."""
        return CurrentFeedResolver().resolve(self.publications(), on=on)
