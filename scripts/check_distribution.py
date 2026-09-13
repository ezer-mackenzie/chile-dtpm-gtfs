"""Install the built wheel outside the checkout and smoke-test the public pipeline.

Run with `uv run python scripts/check_distribution.py` after `uv build`.
Requires uv on PATH and package-index access for wheel dependencies.
"""

import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZipFile

SMOKE = """
import json
from importlib.metadata import entry_points, version
from pathlib import Path
from zipfile import ZipFile
import chile_dtpm_gtfs
from chile_dtpm_gtfs import GTFSFeed

assert version("chile-dtpm-gtfs") == EXPECTED_VERSION
assert not Path(chile_dtpm_gtfs.__file__).resolve().is_relative_to(SOURCE_DIRECTORY)
assert any(item.name == "chile-dtpm-gtfs" for item in entry_points(group="console_scripts"))
records = {
    "agency.txt": "agency_name,agency_url,agency_timezone\\nMetro,https://example.org,America/Santiago\\n",
    "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\\nS,Station,-33.45,-70.65\\n",
    "routes.txt": "route_id,route_short_name,route_type\\nR,L1,1\\n",
    "trips.txt": "route_id,service_id,trip_id\\nR,S,T\\n",
    "stop_times.txt": ("trip_id,arrival_time,departure_time,stop_id,stop_sequence\\n"
                       "T,25:00:00,25:00:00,S,1\\n"),
}
with ZipFile("feed.zip", "w") as archive:
    for name, content in records.items():
        archive.writestr(name, content)
with GTFSFeed.from_file("feed.zip") as feed:
    assert feed.validate().row_counts["stops.txt"] == 1
    snapshot = feed.metro()
snapshot.write_geojson("metro.geojson")
assert len(json.loads(Path("metro.geojson").read_text())["features"]) == 2
print("Installed wheel pipeline passed")
"""


def main() -> None:
    """Check wheel contents, then execute in an isolated temporary environment."""
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = config["project"]["version"]
    wheel = root / "dist" / f"chile_dtpm_gtfs-{version}-py3-none-any.whl"
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "chile_dtpm_gtfs/py.typed" in names
        assert f"chile_dtpm_gtfs-{version}.dist-info/licenses/LICENSE.md" in names
        assert "chile_dtpm_gtfs/cli.py" in names
    with tempfile.TemporaryDirectory(prefix="dtpm-wheel-") as directory:
        work = Path(directory)
        environment = work / "venv"
        subprocess.run(["uv", "venv", "--python", sys.executable, str(environment)], check=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(["uv", "pip", "install", "--python", str(python), str(wheel)], check=True)
        code = f"EXPECTED_VERSION = {version!r}\nSOURCE_DIRECTORY = {str(root / 'src')!r}\n" + SMOKE
        subprocess.run([str(python), "-I", "-c", code], cwd=work, check=True)
        subprocess.run(
            [str(python), "-I", "-m", "chile_dtpm_gtfs", "--version"], cwd=work, check=True
        )


if __name__ == "__main__":
    main()
