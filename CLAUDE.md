# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A CLI tool that syncs Bluetooth pairing keys between Linux and Windows on dual-boot systems. It reads Linux pairing keys from `/var/lib/bluetooth/` and writes them into the Windows registry hive file via `chntpw/reged`. Requires root to run. Fork of [x2es/bt-dualboot](https://github.com/x2es/bt-dualboot), maintained on the `dev` branch.

## Commands

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

## Architecture

```
src/bt_dualboot/
├── __init__.py              # APP_NAME + __version__ via importlib.metadata
├── cli/
│   ├── app.py               # main(), Application class, argparse
│   └── tools.py             # Guards (require_linux, require_chntpw), print helpers
├── models/
│   └── bluetooth_device.py  # BluetoothDevice value object
├── bt_linux/                # Reads /var/lib/bluetooth/ INI files
├── bt_windows/              # Reads Windows registry via WindowsRegistry
│   ├── convert.py           # MAC/key format conversions (hex ↔ registry)
│   └── devices.py
├── bt_sync_manager/
│   └── manager.py           # BtSyncManager: compare keys, push Linux → Windows
└── windows_registry/
    └── registry.py          # WindowsRegistry: wraps chntpw/reged for hive manipulation
```

**Data flow**: `bt_linux/` reads Linux devices → `bt_windows/` reads Windows devices → `bt_sync_manager/` compares and pushes Linux keys into Windows registry via `windows_registry/`.

**Windows registry writes** use `reged -N -E` (rewrite-only, no size change). Backups strongly recommended before writes.

## Type Annotations

All source code uses Python 3.13+ type annotations:
- PEP 604 union syntax: `str | None`
- PEP 585 generic syntax: `list[str]`, `dict[str, str]`
- PEP 695 type aliases: `type DeviceOrMac = str | BluetoothDevice`
- Test fixtures and helpers are annotated; test functions (`test_*`) are not

## Testing

- `tests/conftest.py` — all fixtures (windows_registry with temp SYSTEM hive, test_scheme device/key mapping, sample data paths)
- `tests/_helpers.py` — `pytest_unwrap()` and `bt_linux_sample_01_unwrapped()` for `@patch` decorators
- `tests_integration/` — Docker-based CLI integration tests, imports from `tests.conftest` and `tests._helpers`
- `tests/__init__.py` is kept because integration tests import from it
- Snapshot tests use **syrupy** (`assert value == snapshot`), stored in `__snapshots__/*.ambr`
- Test data: `tests/bt_linux/data_samples/` (Linux BT info files), `tests/windows_registry/data_samples/` (Windows SYSTEM hive + .reg export)

## Configuration

- **pytest**: `importlib` import mode, `testpaths = ["tests"]`
- **ruff**: py313 target, 120 line length, rules: E/W/F/I/UP/B/SIM/TCH
- **Python**: requires >=3.13
- **External dep**: `chntpw` must be installed on the system (provides `reged`)
- **Debug mode**: `DEBUG=1 bt-dualboot` enables verbose output
