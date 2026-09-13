"""Offline contracts for publication discovery and applicability."""

from datetime import date
from pathlib import Path

import httpx
import pytest

from chile_dtpm_gtfs import DTPM
from chile_dtpm_gtfs.exceptions import (
    DTPMSourceError,
    DTPMSourceParseError,
    NoCurrentPublicationError,
)
from chile_dtpm_gtfs.source.dates import parse_spanish_date
from chile_dtpm_gtfs.source.models import SOURCE_URL
from chile_dtpm_gtfs.source.parser import PublicationParser
from chile_dtpm_gtfs.source.resolver import CurrentFeedResolver

HTML = (Path(__file__).parent / "fixtures/dtpm_gtfs_page.html").read_text(encoding="utf-8")


def test_publications() -> None:
    publications = PublicationParser().parse(HTML)
    assert len(publications) == 2
    assert publications[0].effective_from == date(2026, 8, 29)
    assert publications[0].download_url == "https://www.dtpm.cl/downloads/current-release.zip"
    assert publications[1].filename == "special release.zip"
    assert publications[1].description == "+ desvíos elecciones (segunda vuelta)"
    assert "segunda vuelta" in publications[1].title


@pytest.mark.parametrize(
    "month,number",
    list(
        enumerate(
            (
                "enero febrero marzo abril mayo junio julio agosto "
                "septiembre octubre noviembre diciembre"
            ).split(),
            1,
        )
    ),
)
def test_months(month: int, number: str) -> None:
    assert parse_spanish_date(f"2 de {number} de 2026") == date(2026, month, 2)
    assert parse_spanish_date(f"02 de {number.upper()} 2026") == date(2026, month, 2)


@pytest.mark.parametrize("value", ["31 de febrero de 2026", "1 de unknown 2026", "2026-01-01"])
def test_invalid_dates(value: str) -> None:
    with pytest.raises(DTPMSourceParseError):
        parse_spanish_date(value)


@pytest.mark.parametrize(
    "html",
    [
        "<html>Changed page</html>",
        "<p>GTFS Vigente desde 1 de enero 2026</p>",
        '<p>GTFS Vigente desde tomorrow</p><a href="/feed.zip">GTFS</a>',
        '<p>GTFS Vigente desde 1 de enero 2026</p><a href="/a.zip">A</a><a href="/b.zip">B</a>',
    ],
)
def test_invalid_pages(html: str) -> None:
    with pytest.raises(DTPMSourceParseError):
        PublicationParser().parse(html)


def test_single_publication_and_description() -> None:
    result = PublicationParser().parse(
        "<h3>GTFS Vigente desde 1 de enero 2026</h3><p>Special service</p>"
        '<a href="feed.zip?version=2">GTFS</a>',
        source_url="https://www.dtpm.cl/index/page",
    )
    assert len(result) == 1
    assert result[0].description == "Special service"
    assert result[0].download_url == "https://www.dtpm.cl/index/feed.zip?version=2"


def test_resolver() -> None:
    publications = PublicationParser().parse(HTML)
    resolver = CurrentFeedResolver()
    assert resolver.resolve(publications, on=date(2026, 8, 28)) == publications[1]
    assert resolver.resolve(publications, on=date(2026, 8, 29)) == publications[0]
    assert (
        resolver.resolve([publications[0], publications[0]], on=date(2026, 9, 1)) == publications[0]
    )
    for items in ([], publications):
        with pytest.raises(NoCurrentPublicationError):
            resolver.resolve(items, on=date(2020, 1, 1))


def test_facade_only_fetches_html() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(200, text=HTML)

    dtpm = DTPM(transport=httpx.MockTransport(handler))
    assert requests == []
    assert len(dtpm.publications()) == 2
    assert dtpm.current(on=date(2026, 8, 29)).effective_from == date(2026, 8, 29)
    assert requests == [SOURCE_URL, SOURCE_URL]


@pytest.mark.parametrize("status", [404, 500])
def test_http_errors(status: int) -> None:
    with pytest.raises(DTPMSourceError):
        DTPM(transport=httpx.MockTransport(lambda request: httpx.Response(status))).publications()


def test_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timed out", request=request)

    with pytest.raises(DTPMSourceError) as error:
        DTPM(transport=httpx.MockTransport(handler)).publications()
    assert isinstance(error.value.__cause__, httpx.ReadTimeout)


def test_redirect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == SOURCE_URL:
            return httpx.Response(302, headers={"Location": "/new/index"})
        return httpx.Response(
            200, text='<p>GTFS Vigente desde 1 de enero 2026</p><a href="feed.zip">GTFS</a>'
        )

    result = DTPM(transport=httpx.MockTransport(handler)).publications()
    assert result[0].download_url == "https://www.dtpm.cl/new/feed.zip"
