# Releasing

Package versions follow Semantic Versioning (`0.1.0`); Git tags use the `v` prefix
(`v0.1.0`). Completing a local milestone does not automatically upload a package.
All commit messages follow the conventions in AGENTS.md.

## Local release preparation

1. Update the version in pyproject.toml and the dated changelog entry.
2. Run `uv lock`, then all checks documented in [testing](testing.md).
3. Build the wheel and source distribution with `uv build` and run
   `uv run python scripts/check_distribution.py`.
4. Commit a coherent release preparation change and inspect the final working tree.
5. When the version is approved, create an annotated tag:
   `git tag -a v0.1.0 -m "Release v0.1.0"`.

Generated distributions live in dist/ and documentation HTML in site/. Neither is
committed. To preview documentation, run
`uv run --group docs python -m mkdocs serve`.

## GitHub and PyPI setup

The publish.yml workflow uses PyPI Trusted Publishing. Before enabling publication,
configure a PyPI publisher for owner `ezer-mackenzie`, repository
`chile-dtpm-gtfs`, workflow `publish.yml`, and GitHub environment `pypi`. Configure
the `pypi` environment's reviewers/protection rules in GitHub as desired. These
account settings cannot be established by adding workflow files alone.

After explicitly deciding to publish, push the approved commit/tag and publish a
GitHub release for that tag. The workflow also offers a manual dispatch requiring
an existing release tag. It checks that the ref is a version tag matching package
metadata, runs tests/lint/types/docs/build/installed-wheel checks, then uploads
artifacts and publishes through the pypi environment using a short-lived OIDC token.
It does not store a long-lived PyPI API token. Publishing remains subject to the
external account/environment configuration and approvals.

Only published, non-prerelease GitHub releases trigger automatic publication;
draft release creation and ordinary pushes do not. A failed upload must be
investigated rather than replacing an existing PyPI version. PyPI versions are
immutable; prepare a new patch version if released contents need correction.

## Documentation and dependency maintenance

MkDocs and .readthedocs.yaml are configured for English documentation. Import the
repository into a Read the Docs project to activate hosted builds. A strict local
build is part of CI; this does not create or activate the external account.

Codecov configuration targets 90% coverage. CI enforces this locally; configure
the external Codecov project/token to activate its reports.

Dependabot checks Python dependencies and GitHub Actions weekly. Dependency commits
use `build(deps)` and workflow commits use `ci(deps)` to match project conventions.

Primary references: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
and [Read the Docs build customization](https://docs.readthedocs.com/platform/stable/build-customization.html).
