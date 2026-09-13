"""Small exporter contract and atomic JSON artifact writing."""

import json
import os
import tempfile
from pathlib import Path
from typing import Protocol

from chile_dtpm_gtfs.domain.network import TransitNetwork
from chile_dtpm_gtfs.exceptions import FeedExportError

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]


class Exporter(Protocol):
    """An exporter consumes domain data rather than reopening GTFS tables."""

    def to_dict(self, network: TransitNetwork) -> dict[str, JSONValue]:
        """Return a JSON-compatible document."""
        ...


def write_document(
    document: dict[str, JSONValue], path: str | Path, *, overwrite: bool = False
) -> Path:
    """Write UTF-8 JSON atomically, rejecting NaN and accidental replacement."""
    target = Path(path)
    temporary: Path | None = None
    try:
        if target.exists() and not overwrite:
            raise FeedExportError(f"Destination already exists: {target}")
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            suffix=".part",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            json.dump(document, output, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            output.write("\n")
        if overwrite:
            os.replace(temporary, target)
        else:
            os.link(temporary, target)
        return target
    except (OSError, ValueError, TypeError) as exc:
        raise FeedExportError(f"Unable to write {target}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
