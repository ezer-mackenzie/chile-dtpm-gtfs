"""Small generated archives with relationally distinct Metro and bus services."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest


@pytest.fixture
def tables() -> dict[str, str]:
    """Include parent stations, an entrance, shape variants, and calendar exceptions."""
    return {
        "agency.txt": (
            "agency_id,agency_name,agency_url,agency_timezone\n"
            "M,Metro,https://example.org,America/Santiago\n"
            "B,Bus,https://example.org,America/Santiago\n"
        ),
        "stops.txt": (
            "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
            "S,Central,-33.45,-70.65,1,\n"
            "P,Central platform,-33.451,-70.651,0,S\n"
            "E,Central entrance,-33.452,-70.652,2,S\n"
            "Q,Terminal,-33.46,-70.66,0,\n"
            "B,Metro misleading bus stop,-33.47,-70.67,0,\n"
        ),
        "routes.txt": (
            "route_id,agency_id,route_short_name,route_long_name,route_type,route_color\n"
            "R,M,L1,Metro line,1,FF0000\n"
            "B,B,100,Bus route,3,\n"
        ),
        "trips.txt": (
            "route_id,service_id,trip_id,direction_id,shape_id\nR,WK,T,0,A\nR,WK,U,1,Z\nB,WK,B,0,\n"
        ),
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "T,25:10:00,25:11:00,P,1\n"
            "T,25:15:00,25:15:00,Q,2\n"
            "U,06:00:00,06:00:00,Q,1\n"
            "U,06:05:00,06:05:00,P,2\n"
            "B,08:00:00,08:00:00,B,1\n"
        ),
        "shapes.txt": (
            "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
            "A,-33.46,-70.66,2\n"
            "A,-33.45,-70.65,1\n"
            "Z,-33.46,-70.66,1\n"
            "Z,-33.45,-70.65,2\n"
        ),
        "calendar.txt": (
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date\n"
            "WK,1,1,1,1,1,0,0,20260101,20261231\n"
        ),
        "calendar_dates.txt": "service_id,date,exception_type\nWK,20260914,2\nWK,20260913,1\n",
        "feed_info.txt": (
            "feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,"
            "feed_end_date,feed_version\n"
            "Test,https://example.org,es,20260101,20261231,test-version\n"
        ),
    }


def write_archive(path: Path, tables: dict[str, str]) -> Path:
    """Create a UTF-8 archive, never contacting the live source."""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, content in tables.items():
            archive.writestr(name, content.encode("utf-8"))
    return path


@pytest.fixture
def archive_path(tmp_path: Path, tables: dict[str, str]) -> Path:
    return write_archive(tmp_path / "feed.zip", tables)
