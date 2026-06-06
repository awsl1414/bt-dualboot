# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A CLI tool that syncs Bluetooth pairing keys between Linux and Windows on dual-boot systems. It reads Linux pairing keys from `/var/lib/bluetooth/` and writes them into the Windows registry hive file via `chntpw/reged`. Auto-elevates to root via sudo when needed (`--no-elevate` to disable). Fork of [x2es/bt-dualboot](https://github.com/x2es/bt-dualboot), maintained at [awsl1414/bt-dualboot](https://github.com/awsl1414/bt-dualboot) on the `dev` branch. PyPI package: `bt-dualboot-ng`.

## Commands

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

## Architecture (Clean Architecture)

```
src/bt_dualboot/
├── __init__.py              # APP_NAME + __version__ via importlib.metadata
├── _debug.py                # is_debug() singleton
│
├── domain/                  # Pure Python, zero project dependencies
│   ├── enums.py             # PairingType, DeviceSource (StrEnum)
│   ├── models.py            # BluetoothDevice (frozen dataclass)
│   └── protocols.py         # DeviceReader, DeviceWriter (Protocol)
│
├── application/             # Business logic, depends on domain/ only
│   └── sync.py              # SyncService, DeviceNotFoundError
│
├── infrastructure/          # Platform implementations, depends on domain/ only
│   ├── mount.py             # Windows partition discovery
│   ├── linux/
│   │   ├── parser.py        # INI parsing → BluetoothDevice
│   │   └── reader.py        # LinuxDeviceReader(bt_dir=...), read_all()
│   ├── windows/
│   │   ├── parser.py        # Registry section parsing
│   │   ├── reader.py        # WindowsDeviceReader
│   │   ├── convert.py       # hex/MAC/registry conversions (pure functions)
│   │   └── writer.py        # WindowsDeviceWriter
│   └── registry/
│       ├── hive.py          # WindowsRegistry (chntpw/reged wrapper)
│       └── resolve.py       # resolve_path_ci() case-insensitive NTFS path
│
└── cli/                     # CLI interface (composition root)
    ├── main.py              # argparse + Application
    └── privilege.py         # sudo auto-elevation
```

### Dependency Direction

```
domain          ← stdlib only
  ↑
application     ← domain/ only
  ↑
infrastructure  ← domain/ only (never imports application/)
  ↑
cli             ← application/ + domain/ + infrastructure/ (composition root)
[gui]           ← same as cli (future PySide6 GUI)
```

### Key Design Decisions

- **Frozen dataclass**: `BluetoothDevice` is `@dataclass(slots=True, frozen=True, kw_only=True)`. Use `dataclasses.replace()` for mutation.
- **Protocol-based DI**: `DeviceReader`/`DeviceWriter` protocols. CLI/GUI inject concrete implementations into `SyncService`.
- **GUI-ready**: `SyncService` has no print/argparse/I/O. Future PySide6 GUI can directly reuse it.
- **No `__post_init__`**: Auto-derivation logic (pairing_type default, Key injection) lives in parser layer.
- **Parameterized readers**: `LinuxDeviceReader(bt_dir=...)` eliminates `@patch` in tests.
- **Sudo auto-elevation**: `cli/privilege.py` auto re-execs under sudo. `--no-elevate` to disable.
- **Case-insensitive path**: `resolve_path_ci()` handles NTFS mounts where Windows paths differ in case (e.g. `system` vs `SYSTEM`).
- **Unsyncable devices**: `LinuxDeviceReader.read_all()` returns both syncable and unsyncable devices; CLI shows "Missing pairing key" section.
- **Multi-mount interactive selection**: `resolve_windows_location()` returns `list[str]`; when multiple Windows mounts found, `_interactive_select_mount()` prompts user (supports single/comma/range/all). Non-TTY and `--bot` mode raise `SystemExit` with mount list.
- **BT dir error differentiation**: `require_bt_dir_access()` distinguishes three failure cases: directory not found (service down), permission denied (needs sudo), no paired devices (never paired).
- **Structured `run()` flow**: `--list-win-mounts` (no deps) → resolve Windows → single `require_bt_dir_access()` check → `--list` → conditional sync loop with `_reset_windows_state()` per mount.

### Data Flow

`linux/reader` reads `/var/lib/bluetooth/` → `windows/reader` reads registry → `SyncService` compares and pushes via `windows/writer` → `registry/hive` writes via chntpw/reged.

**Windows registry writes** use `reged -N -E` (rewrite-only, no size change). Backups strongly recommended before writes.

## Type Annotations

All source code uses Python 3.13+ type annotations:
- PEP 604 union syntax: `str | None`
- PEP 585 generic syntax: `list[str]`, `dict[str, str]`
- PEP 695 type aliases: `type DeviceOrMac = str | BluetoothDevice`
- Test fixtures and helpers are annotated; test functions (`test_*`) are not

## Testing

- `tests/conftest.py` — all fixtures (windows_registry with temp SYSTEM hive, test_scheme device/key mapping, sample data paths)
- `tests/_helpers.py` — `bt_linux_sample_01_unwrapped()` for path resolution
- Snapshot tests use **syrupy** (`assert value == snapshot`), stored in `__snapshots__/*.ambr`
- Test data: `tests/infrastructure/linux/data_samples/` (Linux BT info files), `tests/infrastructure/registry/data_samples/` (Windows SYSTEM hive + .reg export)
- Tests mirror `src/` structure: `domain/`, `application/`, `infrastructure/`, `cli/`

## Configuration

- **pytest**: `importlib` import mode, `testpaths = ["tests"]`
- **ruff**: py313 target, 120 line length, rules: E/W/F/I/UP/B/SIM/TCH, `known-first-party = ["bt_dualboot"]`
- **Python**: requires >=3.13
- **External dep**: `chntpw` must be installed on the system (provides `reged`)
- **Debug mode**: `DEBUG=1 bt-dualboot` enables verbose output (preserved across sudo elevation)
