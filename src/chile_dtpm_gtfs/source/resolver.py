"""Date-based publication applicability policies."""

from collections.abc import Iterable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from chile_dtpm_gtfs.exceptions import NoCurrentPublicationError
from chile_dtpm_gtfs.source.models import FeedPublication


class CurrentFeedResolver:
    """Choose the greatest applicable date; ties retain the first page entry."""

    def resolve(
        self, publications: Iterable[FeedPublication], *, on: date | None = None
    ) -> FeedPublication:
        """Resolve against an explicit date or today's date in America/Santiago."""
        today = on if on is not None else datetime.now(ZoneInfo("America/Santiago")).date()
        candidates = [item for item in publications if item.effective_from <= today]
        if not candidates:
            raise NoCurrentPublicationError(f"No publication applies on {today.isoformat()}.")
        return max(candidates, key=lambda item: item.effective_from)
