"""Stream archives to disk and preserve download provenance."""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx

from chile_dtpm_gtfs.exceptions import FeedDownloadError


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """An on-disk response and the identity of the exact downloaded bytes."""

    path: Path
    source_url: str
    resolved_url: str
    filename: str
    downloaded_at: datetime
    sha256: str
    size_bytes: int
    content_length: int | None


class FeedDownloader:
    """Download explicitly, with bounded size and atomic destination creation."""

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        max_bytes: int = 2 * 1024**3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Configure per-operation HTTP timeout, byte limit, and optional transport."""
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.transport = transport

    def download(
        self, url: str, destination: str | Path, *, overwrite: bool = False
    ) -> DownloadResult:
        """Write an archive without replacing an existing file unless requested.

        The parent directory must exist. A partial response never becomes the
        destination. SHA-256 covers stored bytes; Content-Length is checked when
        no HTTP content encoding changes their representation.
        """
        target = Path(destination)
        temporary: Path | None = None
        try:
            if urlsplit(url).scheme not in {"http", "https"}:
                raise FeedDownloadError("Download URL must use HTTP or HTTPS.")
            if target.exists() and not overwrite:
                raise FeedDownloadError(f"Destination already exists: {target}")
            with (
                httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                    transport=self.transport,
                    headers={"Accept-Encoding": "identity"},
                ) as client,
                client.stream("GET", url) as response,
            ):
                response.raise_for_status()
                length_header = response.headers.get("content-length")
                length = int(length_header) if length_header is not None else None
                if length is not None and (length < 0 or length > self.max_bytes):
                    raise FeedDownloadError("Response Content-Length exceeds the download limit.")
                digest = hashlib.sha256()
                size = 0
                with tempfile.NamedTemporaryFile(
                    dir=target.parent, suffix=".part", delete=False
                ) as output:
                    temporary = Path(output.name)
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        size += len(chunk)
                        if size > self.max_bytes:
                            raise FeedDownloadError("Response exceeds the download limit.")
                        output.write(chunk)
                        digest.update(chunk)
                if (
                    length is not None
                    and not response.headers.get("content-encoding")
                    and size != length
                ):
                    raise FeedDownloadError(
                        f"Incomplete response: expected {length} bytes, got {size}."
                    )
                if size == 0:
                    raise FeedDownloadError("The response is empty.")
                result = DownloadResult(
                    path=target,
                    source_url=url,
                    resolved_url=str(response.url),
                    filename=unquote(urlsplit(str(response.url)).path.rsplit("/", 1)[-1])
                    or target.name,
                    downloaded_at=datetime.now(UTC),
                    sha256=digest.hexdigest(),
                    size_bytes=size,
                    content_length=length,
                )
            if overwrite:
                os.replace(temporary, target)
            else:
                # Same-directory hard link atomically fails if the target exists.
                os.link(temporary, target)
            return result
        except (httpx.HTTPError, httpx.InvalidURL, OSError, ValueError) as exc:
            raise FeedDownloadError(f"Unable to download {url!r}: {exc}") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
