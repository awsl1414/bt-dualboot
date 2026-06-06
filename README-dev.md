bt-dualboot-ng: Development Guide
=================================

## Development environment

* [uv](https://docs.astral.sh/uv/) — package manager and virtual environment
* Python 3.13+ (managed by uv)
* `chntpw` system package (provides `reged` CLI)

### Bootstrap

```console
$ git clone git@github.com:awsl1414/bt-dualboot.git \
    && cd bt-dualboot \
    && uv sync
```

### Commands

```bash
uv sync                                    # Install package + dev deps
uv run bt-dualboot --version               # Verify CLI works
uv run pytest tests/ -v                    # Run all unit tests
uv run pytest tests/application/test_sync.py -v  # Run single test file
uv run pytest tests/ -v -k "test_get_devices"    # Run tests by name
uv run ruff check src/ tests/              # Lint
uv run ruff format src/ tests/             # Format
uv run ruff check --fix src/ tests/        # Auto-fix lint issues
```

No system python/pip — everything goes through `uv run`.


## Project structure

```
src/bt_dualboot/          # Source code (src-layout, Clean Architecture)
  domain/                 # Pure Python: models, enums, protocols
  application/            # Business logic (SyncService)
  infrastructure/         # Platform implementations (Linux/Windows/Registry)
  cli/                    # CLI interface (composition root)
tests/                    # Unit tests (mirrors src/ structure)
  domain/
  application/
  infrastructure/
    linux/data_samples/   # Linux BT info file fixtures
    registry/data_samples/ # Windows SYSTEM hive fixtures
  cli/__snapshots__/      # syrupy snapshot files
```


## Toolchain

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Package management, virtual environments |
| [ruff](https://docs.astral.sh/ruff/) | Linting + formatting (replaces black, flake8, isort) |
| [pytest](https://docs.pytest.org/) | Test runner, `--import-mode=importlib` |
| [syrupy](https://github.com/syrupy-project/syrupy) | Snapshot testing |


## Testing

```bash
uv run pytest tests/ -v                   # All unit tests
uv run pytest tests/ -v --snapshot-update # Update syrupy snapshots
uv run pytest tests/cli/test_main.py -v --snapshot-update  # Update snapshots
```


## Code style

- **Python 3.13+**: use `str | None`, `list[str]`, `type X = ...` (PEP 604/585/695)
- **Type annotations**: required on all source functions, test fixtures, and helpers
- **Line length**: 120 chars
- **Lint rules**: E/W/F/I/UP/B/SIM/TCH (configured in pyproject.toml)
- **Format**: `ruff format` (no black needed)
- **No magic numbers**: use named constants (e.g. `_DEFAULT_ENC_SIZE`)


## Configuration

All configuration lives in `pyproject.toml`:

- `[tool.pytest.ini_options]` — pytest settings
- `[tool.ruff]` — lint and format settings
- `[tool.ruff.lint.isort]` — import sorting with `known-first-party = ["bt_dualboot"]`
- `[tool.hatch.build.targets.wheel]` — build configuration


## Debug mode

```bash
DEBUG=1 bt-dualboot --sync-all    # Verbose output and artifacts (DEBUG preserved across sudo)
```
