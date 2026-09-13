# Testing

The default test suite never contacts DTPM:

```sh
uv sync --locked
uv run python -m pytest
uv run python -m ruff check .
uv run python -m ruff format --check .
uv run python -m mypy src
```

Fixtures contain synthetic publication HTML and generated minimal ZIPs. They cover
Spanish dates, current/future selection, relative/absolute links, HTTP errors,
redirects, incomplete downloads, SHA-256, invalid ZIP/CSV input, required files,
optional tables, extended service hours, calendars, relational Metro selection,
shape variants, output replacement, CLI behavior, and resource ownership.

CI runs Python 3.12, 3.13, and 3.14 on Linux and Windows. Using `python -m` also
avoids Windows restrictions on generated console launchers. To test another
interpreter locally without replacing the development environment, set
`UV_PROJECT_ENVIRONMENT` to a separate directory (for example `tmp/qa312`) and
use `uv run --python 3.12 python -m pytest`.

## Optional live acceptance

The live test fetches the current page, downloads the official feed, performs a
complete basic validation scan, selects Metro, and writes GeoJSON with provenance.
It uses temporary storage and is skipped unless explicitly enabled:

```sh
# POSIX shells
DTPM_LIVE_TESTS=1 uv run python -m pytest tests/integration -m live
```

```powershell
$env:DTPM_LIVE_TESTS = '1'
uv run python -m pytest tests/integration -m live
Remove-Item Env:DTPM_LIVE_TESTS
```

Live source contents and availability can change. Tests assert pipeline behavior,
not a fixed current filename, publication date, or station count.

## Packaging and documentation

```sh
uv build
uv run python scripts/check_distribution.py
uv run --group docs python -m mkdocs build --strict
```

The distribution check installs the wheel into a fresh environment outside the
checkout, checks the typing marker/license/CLI entry point, and executes a small
local GTFS-to-GeoJSON pipeline. It requires package-index access for dependencies.
The source distribution includes docs, tests, scripts, and the lockfile; the wheel
contains the library, metadata, and license rather than test data or real feeds.

## Coverage

CI runs `uv run python -m pytest --cov=chile_dtpm_gtfs --cov-report=xml`.
The local/CI coverage gate is 90% of statements; codecov.yml preserves the same
project/patch target. One Linux/Python 3.12 job uploads coverage.xml to Codecov.
Configure the Codecov project and CODECOV_TOKEN secret when required by the account.
Upload failures do not bypass the local coverage gate or fail an otherwise valid
build; the external coverage service is supplemental.
