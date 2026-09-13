"""Archive downloading contracts using local HTTP transports."""

import hashlib
from pathlib import Path

import httpx
import pytest

from chile_dtpm_gtfs.exceptions import FeedDownloadError
from chile_dtpm_gtfs.source.downloader import FeedDownloader


def test_download_provenance_and_redirect(tmp_path: Path) -> None:
    content = b"zip payload"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/index":
            return httpx.Response(302, headers={"location": "/a%20feed.zip"})
        return httpx.Response(200, content=content)

    result = FeedDownloader(transport=httpx.MockTransport(handler)).download(
        "https://example.org/index", tmp_path / "feed.zip"
    )
    assert result.path.read_bytes() == content
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert result.size_bytes == result.content_length == len(content)
    assert result.filename == "a feed.zip"
    assert result.source_url.endswith("/index")
    assert result.resolved_url.endswith("/a%20feed.zip")
    assert result.downloaded_at.utcoffset() is not None
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.parametrize(
    "status,headers,content,max_bytes",
    [
        (404, {}, b"missing", 100),
        (200, {"content-length": "12"}, b"short", 100),
        (200, {"content-length": "invalid"}, b"x", 100),
        (200, {}, b"too large", 3),
        (200, {}, b"", 100),
    ],
)
def test_failures_leave_no_archive(
    tmp_path: Path,
    status: int,
    headers: dict[str, str],
    content: bytes,
    max_bytes: int,
) -> None:
    downloader = FeedDownloader(
        max_bytes=max_bytes,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, headers=headers, content=content)
        ),
    )
    with pytest.raises(FeedDownloadError):
        downloader.download("https://example.org/feed.zip", tmp_path / "feed.zip")
    assert list(tmp_path.iterdir()) == []


def test_overwrite_is_explicit(tmp_path: Path) -> None:
    target = tmp_path / "feed.zip"
    target.write_bytes(b"original")
    downloader = FeedDownloader(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"replacement"))
    )
    with pytest.raises(FeedDownloadError, match="already exists"):
        downloader.download("https://example.org/feed.zip", target)
    assert target.read_bytes() == b"original"
    downloader.download("https://example.org/feed.zip", target, overwrite=True)
    assert target.read_bytes() == b"replacement"


def test_timeout_keeps_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "feed.zip"
    target.write_bytes(b"original")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(FeedDownloadError):
        FeedDownloader(transport=httpx.MockTransport(handler)).download(
            "https://example.org/feed.zip", target, overwrite=True
        )
    assert target.read_bytes() == b"original"
