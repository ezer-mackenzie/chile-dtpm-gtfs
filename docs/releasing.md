# Releasing

Package versions follow Semantic Versioning. Version `1.0.0` is tagged as
`v1.0.0`; this guide describes the process for preparing subsequent versions.
Replace `X.Y.Z` below with the intended version. A commit or tag does not by itself
create a GitHub release or upload a package. All commit messages follow the
conventions in AGENTS.md.

## v1.0 API stability

The documented APIs in [api.md](api.md), their typed domain records, documented
errors, selectors, and exporter outputs are the compatibility surface. Internal
modules not named in public guides may change without a compatibility promise.
After v1.0.0, incompatible changes to the documented surface require a major
version and migration guidance. Pre-1.0 minor releases may evolve APIs, with
behavior changes recorded in the changelog.

## Local release preparation

1. Update the version in pyproject.toml and the dated changelog entry.
2. Run `uv lock`, then all checks documented in [testing](testing.md).
3. Build the wheel and source distribution with `uv build` and run
   `uv run python scripts/check_distribution.py`.
4. Commit a coherent release preparation change and inspect the final working tree.
5. After explicit release approval, create an annotated tag for the prepared
   version, for example: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.

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
