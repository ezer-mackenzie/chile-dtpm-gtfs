"""Parse publication blocks without fetching HTML or resolving applicability."""

import re
from urllib.parse import unquote, urljoin, urlsplit

from selectolax.parser import HTMLParser

from chile_dtpm_gtfs.exceptions import DTPMSourceParseError
from chile_dtpm_gtfs.source.dates import DATE_PATTERN, parse_spanish_date
from chile_dtpm_gtfs.source.models import SOURCE_URL, FeedPublication

MARKER = re.compile(r"GTFS\s+Vigente\s+desde", re.I)


class PublicationParser:
    """Read paragraph/heading publication blocks followed by ZIP anchors.

    Preserve document order and descriptive text (with whitespace normalized).
    Reject incomplete blocks rather than returning a potentially stale subset.
    """

    def parse(self, html: str, *, source_url: str = SOURCE_URL) -> list[FeedPublication]:
        """Extract actual hrefs, resolving relative links against the source page."""
        tree = HTMLParser(html)
        publications: list[FeedPublication] = []
        title: str | None = None
        description: list[str] = []
        date_text = ""
        links: list[str] = []

        def finish() -> None:
            if title is None:
                return
            if len(links) != 1:
                raise DTPMSourceParseError(
                    f"Expected one ZIP link for {title!r}; found {len(links)}."
                )
            url = links[0]
            publications.append(
                FeedPublication(
                    title=title,
                    source_page=source_url,
                    effective_from=parse_spanish_date(date_text),
                    download_url=url,
                    filename=unquote(urlsplit(url).path.rsplit("/", 1)[-1]),
                    description=" ".join(description) or None,
                )
            )

        root = tree.root
        if root is None:
            raise DTPMSourceParseError("The publication page is empty.")
        for node in root.traverse():
            if node.tag not in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "a"}:
                continue
            content = " ".join(node.text(separator="", strip=False).split())
            marker = MARKER.search(content) if node.tag != "a" else None
            if marker:
                finish()
                title, description, links = content, [], []
                date_start = marker.end()
                while date_start < len(content) and content[date_start].isspace():
                    date_start += 1
                match = DATE_PATTERN.match(content, date_start)
                if match is None:
                    raise DTPMSourceParseError(f"Missing publication date in {title!r}")
                date_text = match.group()
                parse_spanish_date(date_text)
                extra = content[match.end() :].strip()
                if extra:
                    description.append(extra)
            elif title is not None and node.tag == "a":
                href = node.attributes.get("href", "")
                url = urljoin(source_url, href)
                parts = urlsplit(url)
                if parts.path.lower().endswith(".zip"):
                    if parts.scheme not in {"http", "https"} or not parts.netloc:
                        raise DTPMSourceParseError(f"Invalid download URL: {url!r}")
                    if url not in links:
                        links.append(url)
            elif title is not None and content and not links:
                description.append(content)
        finish()
        if not publications:
            raise DTPMSourceParseError(
                "No DTPM publication blocks found; the page may have changed."
            )
        return publications
