# Downloads

`source.downloader.FeedDownloader().download(url, destination)` streams an explicit
HTTP(S) URL to a file. The destination parent must exist. Existing files require
`overwrite=True`; failed downloads leave the destination unchanged. Temporary
files are cleaned up. The default response limit is 2 GiB and the HTTP timeout is
60 seconds per operation; both are configurable on the downloader.

`DownloadResult` exposes the path, requested and resolved URLs, decoded URL
filename, UTC completion timestamp, SHA-256 of the stored bytes, actual size, and
advertised Content-Length. Content-Disposition is not used as a filesystem path.
Redirects are followed. HTTP errors, timeouts, oversized/truncated/empty responses,
and filesystem failures raise `FeedDownloadError`.

This layer downloads bytes only. Archive validation belongs to the GTFS layer.
