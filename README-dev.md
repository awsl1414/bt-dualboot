bt-dualboot: Development Guide
==============================

## Development environment

* [uv](https://docs.astral.sh/uv/) — package manager and virtual environment
* Python 3.13+ (managed by uv)
* `chntpw` system package (provides `reged` CLI)

### Bootstrap

```console
$ git clone git@github.com:x2es/bt-dualboot.git \
    && cd bt-dualboot \
    && uv sync
```

### Commands

```bash
uv sync                                    # Install package + dev deps
uv run bt-dualboot --version               # Verify CLI works
uv run pytest tests/ -v                    # Run all unit tests
uv run pytest tests/bt_linux/test_devices.py -v  # Run single test file
uv run pytest tests/ -v -k "test_get_devices"    # Run tests by name
uv run ruff check src/ tests/ tests_integration/  # Lint
uv run ruff format src/ tests/ tests_integration/ # Format
uv run ruff check --fix src/ tests/ tests_integration/  # Auto-fix lint issues
```

No system python/pip — everything goes through `uv run`.


## Project structure

```
src/bt_dualboot/          # Source code (src-layout)
tests/                    # Unit tests
  conftest.py             # Shared fixtures
  _helpers.py             # Test utilities
tests_integration/        # Docker-based integration tests
  helpers.py              # CLI test helpers
  cli/env_*/              # Per-environment test suites
```


## Toolchain

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Package management, virtual environments |
| [ruff](https://docs.astral.sh/ruff/) | Linting + formatting (replaces black, flake8, isort) |
| [pytest](https://docs.pytest.org/) | Test runner, `--import-mode=importlib` |
| [syrupy](https://github.com/syrupy-project/syrupy) | Snapshot testing (replaces pytest-snapshot) |
| [time-machine](https://github.com/adamchainz/time-machine) | Time mocking (replaces libfaketime) |


## Testing

### Unit tests (`tests/`)

```bash
uv run pytest tests/ -v                   # All unit tests
uv run pytest tests/ -v --snapshot-update # Update syrupy snapshots
```

### Integration tests (`tests_integration/`)

Integration tests require Docker and run the actual CLI binary with `sudo`.
They are designed for Docker-based environments.

```bash
# Run in Docker (requires docker)
docker compose -f tests_integration/docker-compose.yml up
```

### Snapshot tests

Snapshots use [syrupy](https://github.com/syrupy-project/syrupy) with the `assert value == snapshot` pattern.
Snapshot files are stored in `__snapshots__/test_file.ambr`.

```bash
uv run pytest tests/cli/test_tools.py -v --snapshot-update  # Update snapshots
```


## Code style

- **Python 3.13+**: use `str | None`, `list[str]`, `type X = ...` (PEP 604/585/695)
- **Type annotations**: required on all source functions, test fixtures, and helpers
- **Line length**: 120 chars
- **Lint rules**: E/W/F/I/UP/B/SIM/TCH (configured in pyproject.toml)
- **Format**: `ruff format` (no black needed)


## Configuration

All configuration lives in `pyproject.toml`:

- `[tool.pytest.ini_options]` — pytest settings
- `[tool.ruff]` — lint and format settings
- `[tool.hatch.build.targets.wheel]` — build configuration


## Debug mode

```bash
DEBUG=1 sudo bt-dualboot --sync-all    # Verbose output and artifacts
```
