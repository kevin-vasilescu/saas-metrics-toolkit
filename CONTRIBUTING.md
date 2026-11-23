# Contributing

1. Fork and clone the repository.
2. Create a virtual environment and run `pip install -e ".[dev]"` then `pre-commit install`.
3. Make your change with tests. Metric tests must use hand-calculated expected values, with the arithmetic in comments.
4. Run `make check` (ruff, mypy --strict, pytest with 90% coverage).
5. Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`) and open a pull request.

Report bugs and request features through the issue templates.
