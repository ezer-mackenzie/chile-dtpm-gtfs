# Contributing

Use Python 3.12+ and uv. Run `uv sync`, then `uv run pytest`, `uv run ruff check .`,
`uv run ruff format --check .`, and `uv run mypy src` before submitting a change.
Use `uv run ruff format .` to format code. CI covers Python 3.12 and 3.14 on Linux
and Windows. Write code, docstrings, documentation, and commit messages in English;
Spanish official source text belongs in fixtures and preserved metadata.

Follow the current phase in docs/roadmap.md. Add offline behavioral tests for
changes to source parsing or resolution. Do not download real feeds in unit tests.
Use Conventional Commits, Semantic Versioning, and v-prefixed release tags. Explain
new dependencies and update user documentation when behavior changes.

## Commits

Follow the commit conventions in [AGENTS.md](AGENTS.md#commit-conventions).
Use English Conventional Commit messages and separate changes by coherent feature
or responsibility. Keep implementation and required tests together, and commit
dependency manifests with their lockfile. Examples:

```text
feat(source): discover DTPM publications and resolve the current feed
fix(source): resolve relative download links after redirects
build(deps): configure discovery dependencies and quality tools
ci: check supported Python versions on Linux and Windows
docs: document discovery usage and the implementation roadmap
chore(repo): configure ignore patterns and line endings
```
