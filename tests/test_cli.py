"""Offline command-line contracts against the real library APIs."""

import json
from datetime import date
from importlib.metadata import version as package_version
from pathlib import Path

import pytest
from conftest import write_archive
from typer.testing import CliRunner

from chile_dtpm_gtfs import DTPM, FeedPublication, GTFSFeed
from chile_dtpm_gtfs.cli import app
from chile_dtpm_gtfs.exceptions import DTPMSourceError

runner = CliRunner()


def test_help_and_version() -> None:
    assert runner.invoke(app, ["--help"]).exit_code == 0
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == package_version("chile-dtpm-gtfs")


def test_discovery_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    publication = FeedPublication(
        "Test", date(2026, 1, 1), "https://example.org/feed.zip", "feed.zip"
    )
    monkeypatch.setattr(DTPM, "publications", lambda self: [publication])
    result = runner.invoke(app, ["publications"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["download_url"] == publication.download_url
    result = runner.invoke(app, ["current", "--on", "2026-01-01"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["effective_from"] == "2026-01-01"


def test_download_command(
    monkeypatch: pytest.MonkeyPatch, archive_path: Path, tmp_path: Path
) -> None:
    calls: list[str] = []

    def from_url(url: str, *, destination: Path, timeout: float) -> GTFSFeed:
        calls.append(url)
        assert timeout == 60.0
        destination.write_bytes(archive_path.read_bytes())
        return GTFSFeed.from_file(destination)

    monkeypatch.setattr(GTFSFeed, "from_url", from_url)
    target = tmp_path / "download.zip"
    result = runner.invoke(
        app, ["download", "--url", "https://example.org/test.zip", "--output", str(target)]
    )
    assert result.exit_code == 0, result.output
    assert calls == ["https://example.org/test.zip"]
    assert json.loads(result.stdout)["path"] == str(target)
    assert target.exists()


def test_validate_and_export(archive_path: Path, tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(archive_path)])
    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["valid"]
    assert report["row_counts"]["routes.txt"] == 2
    assert report["diagnostics"] == []
    output = tmp_path / "metro.geojson"
    result = runner.invoke(
        app, ["export", "metro", "--input", str(archive_path), "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert len(json.loads(output.read_text())["features"]) == 6
    normalized = tmp_path / "metro.json"
    result = runner.invoke(
        app,
        [
            "export",
            "metro",
            "--input",
            str(archive_path),
            "--format",
            "json",
            "--output",
            str(normalized),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(normalized.read_text())["schema_version"] == 1


def test_validate_reports_semantic_errors(tmp_path: Path, tables: dict[str, str]) -> None:
    tables["routes.txt"] += "INVALID,M,Invalid,Invalid route,99,\n"
    archive = write_archive(tmp_path / "invalid-semantics.zip", tables)
    result = runner.invoke(app, ["validate", str(archive)])

    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert not report["valid"]
    assert report["diagnostics"][0]["code"] == "invalid_route_type"


def test_errors_are_actionable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fail(self: DTPM) -> list[FeedPublication]:
        raise DTPMSourceError("Source unavailable")

    monkeypatch.setattr(DTPM, "publications", fail)
    result = runner.invoke(app, ["publications"])
    assert result.exit_code == 1
    assert "Source unavailable" in result.output
    invalid = tmp_path / "invalid.zip"
    invalid.write_bytes(b"not a zip")
    result = runner.invoke(app, ["validate", str(invalid)])
    assert result.exit_code == 1
    assert "Unable to load GTFS" in result.output


@pytest.mark.parametrize(
    "arguments",
    [
        ["current", "--on", "invalid"],
        ["export", "metro", "--format", "topojson", "--output", "out.json"],
        ["publications", "--timeout", "0"],
    ],
)
def test_bad_arguments(arguments: list[str]) -> None:
    assert runner.invoke(app, arguments).exit_code == 2
