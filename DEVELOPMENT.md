# Development Guide

Developer setup, project layout, and contribution conventions for **bt-dualboot-ng** (CLI: `bt-dualboot`).

User-facing docs: [README.md](README.md) · [简体中文](README.zh-CN.md)

---

## Development environment

- [uv](https://docs.astral.sh/uv/) — package manager and virtual environments
- Python 3.13+ (managed by uv)
- System package `chntpw` (provides the `reged` CLI)

### Bootstrap

```console
$ git clone git@github.com:awsl1414/bt-dualboot.git \
    && cd bt-dualboot \
    && uv sync
```

### Commands

```bash
uv sync                                         # Install package + dev deps
uv run bt-dualboot --version                    # Verify CLI works (Linux only)
uv run pytest tests/ -v                         # Run all unit tests
uv run pytest tests/application/test_sync.py -v # Run a single test file
uv run pytest tests/ -v -k "test_get_devices"   # Run tests by name
uv run ruff check src/ tests/                   # Lint
uv run ruff format src/ tests/                  # Format
uv run ruff check --fix src/ tests/             # Auto-fix lint issues
```

Do not use system `python` / `pip` for this project — run everything through `uv run`.

---

## Project structure

```
src/bt_dualboot/           # Source (src-layout, Clean Architecture)
  domain/                  # Pure Python: models, enums, protocols
  application/             # Business logic (SyncService)
  infrastructure/          # Platform I/O (Linux / Windows / Registry)
  cli/                     # CLI composition root
tests/                     # Unit tests (mirrors src/)
  domain/
  application/
  infrastructure/
    linux/data_samples/    # Linux BT info fixtures
    registry/data_samples/ # Windows SYSTEM hive fixtures
  cli/__snapshots__/       # syrupy snapshots
```

Architecture notes for AI/tooling assistants live in [CLAUDE.md](CLAUDE.md).

---

## Toolchain

| Tool | Purpose |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | Package management, virtual environments |
| [ruff](https://docs.astral.sh/ruff/) | Lint + format (replaces black / flake8 / isort) |
| [pytest](https://docs.pytest.org/) | Test runner (`--import-mode=importlib`) |
| [syrupy](https://github.com/syrupy-project/syrupy) | Snapshot testing |

---

## Testing

```bash
uv run pytest tests/ -v                         # All unit tests
uv run pytest tests/ -v --snapshot-update       # Update syrupy snapshots
uv run pytest tests/cli/test_main.py -v --snapshot-update
```

Notes:

- Fixtures live in `tests/conftest.py` (temp SYSTEM hive, sample paths, device/key scheme).
- Path helpers: `tests/_helpers.py`.
- Snapshot assertions: `assert value == snapshot` → `__snapshots__/*.ambr`.

---

## Code style

- **Python 3.13+**: `str | None`, `list[str]`, `type X = ...` (PEP 604 / 585 / 695)
- **Type annotations**: required on source functions, fixtures, and helpers; not required on `test_*` functions
- **Line length**: 120
- **Lint rules**: E / W / F / I / UP / B / SIM / TCH (`pyproject.toml`)
- **Format**: `ruff format` only
- Prefer named constants over magic numbers (e.g. `_DEFAULT_ENC_SIZE`)

---

## Configuration

All tool config is in `pyproject.toml`:

- `[tool.pytest.ini_options]` — pytest
- `[tool.ruff]` / `[tool.ruff.lint]` — lint and format
- `[tool.ruff.lint.isort]` — `known-first-party = ["bt_dualboot"]`
- `[tool.hatch.build.targets.wheel]` — packaging

---

## Debug mode

```bash
DEBUG=1 bt-dualboot -a    # Verbose output; DEBUG is preserved across sudo elevation
```

The live CLI only runs on Linux (`ERROR: Intended to be used only from Linux.` on other platforms). Unit tests can still be run on macOS/Windows via `uv run pytest`.
