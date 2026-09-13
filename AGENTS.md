# Agent instructions

Build chile-dtpm-gtfs, an unofficial Python 3.12+ library specializing in official
DTPM GTFS distribution. Read README.md, docs/architecture.md, and docs/roadmap.md
before making changes. All code, documentation, and commit messages use English.
Preserve Spanish source wording in metadata and test fixtures.

Implement phases in order. Phase 1 is publication discovery only. Do not implement
the entire roadmap in one change. Inspect existing files, explain substantial
architecture changes, and keep increments small and tested.

Separate HTTP, HTML parsing, immutable publication metadata, applicability,
downloads, GTFS loading, normalized domain, selectors, and exporters. Never build
a ZIP URL from a date or hardcode a current feed. current() returns metadata only.
Use actual hrefs, explicit HTTP/parse errors, and no stale fallback. Preserve
special-service descriptions; exclude future publications using Santiago dates.

Future GTFS work must support explicit URLs and local files, SHA-256 provenance,
optional files, times exceeding 24 hours, calendar exceptions, all shape variants,
and relationship-based Metro selection. Never identify Metro stops by name.
Keep publication dates separate from internal feed dates. Export from domain
models, retain WGS84 longitude/latitude, and do not beautify source geometry.

Use uv, typed public APIs, small functions, pytest, Ruff, and strict mypy. Avoid
unnecessary Any, wrapper classes, dependencies, or placeholder modules. HTTP uses
httpx; HTML uses selectolax. Heavy tabular processing may use Polars when needed.
No Selenium/Playwright, web frameworks, databases, or KMP application code.

After each significant phase run:
- uv run pytest
- uv run ruff check .
- uv run ruff format --check .
- uv run mypy src

Fix failures before proceeding. Tests use local HTML and generated GTFS fixtures;
live integration checks must be optional and separate. Update documentation with
behavior changes. Use Conventional Commits and Semantic Versioning: package
0.1.0, Git tag v0.1.0. Do not publish a release implicitly.

## Commit conventions

Use Conventional Commits: `type(scope): imperative summary`. Scope is optional;
use a meaningful component such as `source`, `deps`, or `repo`. Write messages
in English, keep the subject concise (prefer at most 72 characters), and explain
motivation or important tradeoffs in the body when needed.

Choose the type according to the actual change:

- `feat`: add user-facing functionality.
- `fix`: correct existing behavior; include a regression test when appropriate.
- `refactor`: restructure code without changing behavior.
- `test`: add or improve tests independently of a feature or fix.
- `docs`: change documentation or contributor/agent guidance.
- `build`: change packaging, build tooling, or dependencies.
- `ci`: change continuous integration workflows.
- `chore`: repository maintenance that does not change library behavior.
- `perf`: improve performance without changing expected behavior.

Group commits by one coherent feature or responsibility, not by file extension.
Keep feature/fix implementation and its required tests together. Include directly
related documentation when practical; broad project documentation can be separate.
Keep dependency manifests and lockfile changes together. Do not split coupled
changes into commits that leave imports, tests, or packaging broken. Order commits
so prerequisites precede the features that use them. Avoid unrelated changes,
empty placeholders, generated artifacts, secrets, and vague messages like `update`.
Do not manufacture a fix commit for a bug corrected before its feature was committed.

Mark breaking public API changes with `!` and explain them in a `BREAKING CHANGE:`
footer. Inspect `git diff --cached` before each commit and use explicit paths for
staging. Run the required quality checks before committing the completed change.
Report the resulting commit hashes and any files deliberately left uncommitted.
Do not amend or rewrite existing history, push, tag, or publish unless requested.
