"""Command-line presentation; all discovery and GTFS behavior lives in the library."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from chile_dtpm_gtfs import DTPM, FeedPublication, GTFSFeed
from chile_dtpm_gtfs.exceptions import DTPMError
from chile_dtpm_gtfs.exporters.geojson import metadata_dict

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Discover, download, validate, and export official DTPM GTFS data.",
)
export_app = typer.Typer(no_args_is_help=True, help="Export normalized transit subsets.")
app.add_typer(export_app, name="export")


@contextmanager
def _errors() -> Iterator[None]:
    try:
        yield
    except (DTPMError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("Use a date in YYYY-MM-DD format.") from exc


def _publication(item: FeedPublication) -> dict[str, str | None]:
    return {
        "title": item.title,
        "effective_from": item.effective_from.isoformat(),
        "download_url": item.download_url,
        "filename": item.filename,
        "description": item.description,
        "source_page": item.source_page,
    }


@app.callback(invoke_without_command=True)
def main(
    show_version: Annotated[bool, typer.Option("--version", help="Show package version.")] = False,
) -> None:
    """Access the DTPM publication index and local or remote GTFS archives."""
    if show_version:
        typer.echo(version("chile-dtpm-gtfs"))
        raise typer.Exit()


@app.command()
def publications(timeout: Annotated[float, typer.Option(min=0.1)] = 30.0) -> None:
    """List discovered publications as JSON without downloading a feed."""
    with _errors():
        typer.echo(
            json.dumps(
                [_publication(item) for item in DTPM(timeout=timeout).publications()],
                ensure_ascii=False,
                indent=2,
            )
        )


@app.command()
def current(
    on: Annotated[
        str | None, typer.Option(help="Publication applicability date (YYYY-MM-DD).")
    ] = None,
    timeout: Annotated[float, typer.Option(min=0.1)] = 30.0,
) -> None:
    """Print the applicable publication as JSON; default date is today in Santiago."""
    when = _date(on)
    with _errors():
        typer.echo(
            json.dumps(
                _publication(DTPM(timeout=timeout).current(on=when)), ensure_ascii=False, indent=2
            )
        )


@app.command()
def download(
    output: Annotated[Path, typer.Option("--output", "-o", help="New archive destination.")] = Path(
        "GTFS.zip"
    ),
    url: Annotated[
        str | None, typer.Option(help="Explicit URL; bypass publication discovery.")
    ] = None,
    timeout: Annotated[float, typer.Option(min=0.1)] = 60.0,
) -> None:
    """Download the current or explicit feed, check its structure, and print provenance."""
    with _errors():
        feed = (
            GTFSFeed.from_url(url, destination=output, timeout=timeout)
            if url
            else DTPM(timeout=timeout).current().download(destination=output, timeout=timeout)
        )
        with feed:
            typer.echo(
                json.dumps(
                    {"path": str(feed.path), "metadata": metadata_dict(feed.metadata)},
                    ensure_ascii=False,
                    indent=2,
                )
            )


@app.command()
def validate(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Run basic structural/CSV/time validation on a local ZIP and print row counts."""
    with _errors(), GTFSFeed.from_file(path) as feed:
        report = feed.validate()
        typer.echo(
            json.dumps(
                {"valid": True, "validation": "basic", "row_counts": report.row_counts}, indent=2
            )
        )


@export_app.command("metro")
def export_metro(
    output: Annotated[Path, typer.Option("--output", "-o", help="GeoJSON destination.")],
    input_path: Annotated[
        Path | None, typer.Option("--input", exists=True, dir_okay=False, readable=True)
    ] = None,
    url: Annotated[
        str | None, typer.Option(help="Explicit URL instead of the official current feed.")
    ] = None,
    format_name: Annotated[str, typer.Option("--format")] = "geojson",
    on: Annotated[str | None, typer.Option(help="Optional service date (YYYY-MM-DD).")] = None,
    overwrite: Annotated[bool, typer.Option(help="Replace an existing GeoJSON file.")] = False,
    timeout: Annotated[float, typer.Option(min=0.1)] = 60.0,
) -> None:
    """Export Metro from a local ZIP, explicit URL, or the official current feed."""
    if input_path is not None and url is not None:
        raise typer.BadParameter("Choose either --input or --url.")
    if format_name != "geojson":
        raise typer.BadParameter("Only geojson is supported in this release.")
    when = _date(on)
    with _errors():
        if input_path is not None:
            feed = GTFSFeed.from_file(input_path)
        elif url is not None:
            feed = GTFSFeed.from_url(url, timeout=timeout)
        else:
            feed = DTPM(timeout=timeout).current().download(timeout=timeout)
        with feed:
            result = feed.metro(on=when).write_geojson(output, overwrite=overwrite)
            typer.echo(str(result))
