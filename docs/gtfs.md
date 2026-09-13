# GTFS loading and validation

```python
from chile_dtpm_gtfs import GTFSFeed

with GTFSFeed.from_file("GTFS.zip") as feed:
    print(feed.metadata.sha256)
    print(feed.tables)
    report = feed.validate()
    print(report.row_counts)
```

`GTFSFeed.from_url(url, destination=None, timeout=60.0, max_bytes=...)` combines
explicit download with loading. `publication.download(...)` uses the same API and
adds the source page and advertised effective date. With no destination, use a
context manager or `close()` to remove the owned temporary archive. A supplied
local file or explicit destination is never removed on close. Failed validation
of an explicit download leaves that file available for diagnosis.

Loading indexes one ZIP, checks required tables and CSV headers, reads feed_info,
and computes SHA-256. It does not materialize large tables. Keep the archive
unchanged until close; later access detects size/mtime changes. Metadata exposes
internal feed_start_date/feed_end_date/feed_version independently of publication
applicability. A missing feed_info table is valid.

The five required tables are agency, stops, routes, trips, and stop_times. Calendar,
calendar_dates, shapes, feed_info, transfers, pathways, levels, and frequencies
are optional in this initial loader. `rows("table.txt")` streams string dictionaries;
absent optional tables are empty. Unknown text tables remain accessible. The
normal public domain API is added by the selection layer, not by exposing DataFrames.

The loader accepts UTF-8 with or without BOM and either root tables or a common
wrapper directory. It rejects duplicate table names, unsafe member paths, invalid
headers, and inconsistent CSV column counts. It never extracts archive members.
The default expanded ZIP limit is 8 GiB and the member limit is 1,000; advanced
callers can configure expanded size with `GTFSLoader`.

`validate()` consumes all CSV records, checks ZIP CRCs for those tables and service
time syntax, and reports record counts. This is basic structural validation, not
certification against every conditional rule in the GTFS specification. Use a
full external GTFS validator for that purpose. `parse_service_time("25:10:00")`
returns 90600 service seconds; blank intermediate times remain optional values.
