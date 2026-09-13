"""Public errors raised by the library."""


class DTPMError(Exception):
    """Base exception for library failures."""


class DTPMSourceError(DTPMError):
    """The publication page could not be retrieved."""


class DTPMSourceParseError(DTPMError):
    """The publication page contains missing or invalid metadata."""


class NoCurrentPublicationError(DTPMError):
    """No discovered publication applies on the requested date."""


class FeedDownloadError(DTPMError):
    """An archive could not be downloaded or written completely."""


class InvalidGTFSFeedError(DTPMError):
    """An archive or supported GTFS record is invalid."""


class FeedExportError(DTPMError):
    """A normalized dataset could not be exported."""
