import argparse
import glob
import os
import re
import shutil
import sys
from argparse import ArgumentParser, ArgumentTypeError
from collections.abc import Generator
from contextlib import contextmanager

from bt_dualboot import APP_NAME, __version__
from bt_dualboot._debug import is_debug
from bt_dualboot.application.sync import DeviceNotFoundError, SyncService
from bt_dualboot.domain.models import BluetoothDevice
from bt_dualboot.infrastructure.linux.reader import LinuxDeviceReader
from bt_dualboot.infrastructure.mount import locate_windows_mount_points
from bt_dualboot.infrastructure.registry.hive import WindowsRegistry
from bt_dualboot.infrastructure.windows.reader import WindowsDeviceReader
from bt_dualboot.infrastructure.windows.writer import WindowsDeviceWriter

DEFAULT_BACKUP_PATH: str = os.path.join(os.sep, "var", "backup", "bt-dualboot")


def mac_str(argument_value: str) -> str:
    value = argument_value.upper()
    if re.match("^[A-F0-9:]+$", value) is None:
        raise ArgumentTypeError(
            "unexpected characters! Allowed letters A-F, digits 0-9 and colon, use space as separator."
        )
    return value


def _argv_parser() -> ArgumentParser:
    arg_parser = ArgumentParser(
        prog=APP_NAME,
        description=f"Sync bluetooth keys from Linux to Windows (v{__version__})",
    )

    args_list = arg_parser.add_argument_group("List resources")
    args_sync = arg_parser.add_argument_group("Sync keys")
    args_backup = arg_parser.add_argument_group("Backup Windows Registry")

    arg_parser.add_argument("--version", help="print version", action="store_true")
    args_list.add_argument("-l", "--list", help="[root required] list bluetooth devices", action="store_true")
    args_list.add_argument("--list-win-mounts", help="list mounted Windows locations", action="store_true")
    args_list.add_argument("--bot", help="parsable output for robots (supported: -l)", action="store_true")
    args_sync.add_argument("-d", "--dry-run", help="print actions to do without invocation", action="store_true")
    args_sync.add_argument("-w", "--win", help="Windows mount point (advanced usage)", nargs=1, metavar="MOUNT")
    args_sync.add_argument(
        "-s", "--sync", help="[root required] sync specified device", nargs="+", metavar="MAC", type=mac_str
    )
    args_sync.add_argument("-a", "--sync-all", help="[root required] sync all paired devices", action="store_true")
    args_backup.add_argument("-n", "--no-backup", help="process without backup", action="store_true")
    args_backup.add_argument(
        "-b",
        "--backup",
        help=f"path to backup directory, default: {DEFAULT_BACKUP_PATH}",
        nargs="?",
        metavar="path",
        default=False,
    )
    arg_parser.add_argument("--no-elevate", help="do not auto-elevate to root via sudo", action="store_true")

    return arg_parser


def _opt_backup(value: bool | str | None) -> bool | str | None:
    if value is False:
        return None
    if value is None:
        return True
    return value


@contextmanager
def no_device_error_handler() -> Generator[None]:
    try:
        yield
    except DeviceNotFoundError as err:
        message = err.args[0]
        raise SystemExit(f"ERROR: {message}\nNothing changed.") from None
    except PermissionError as err:
        message = err.args[0]
        raise SystemExit(f"ERROR: {message}\nNothing changed.") from None


def _invariant_and_halt(condition: bool, error_message: str) -> None:
    if condition:
        raise SystemExit(f"ERROR: {error_message}")


def require_linux() -> None:
    _invariant_and_halt(sys.platform.find("linux") != 0, "Intended to be used only from Linux.")


_BT_DIR = "/var/lib/bluetooth"


def require_bt_dir_access() -> None:
    if not os.path.exists(_BT_DIR):
        raise SystemExit(
            f"ERROR: Bluetooth directory not found: {_BT_DIR}\n"
            "Make sure Bluetooth service is running and a Bluetooth adapter is present."
        )

    if not os.access(_BT_DIR, os.R_OK):
        raise SystemExit(f"ERROR: Permission denied: {_BT_DIR}\nRun with sudo to access Bluetooth configuration.")

    has_devices = bool(glob.glob(os.path.join(_BT_DIR, "*", "*", "info")))
    if not has_devices:
        raise SystemExit(
            "ERROR: No paired Bluetooth devices found.\n"
            "Pair at least one device in Linux first, then run this tool to sync."
        )


def require_chntpw_package() -> None:
    _invariant_and_halt(
        shutil.which("reged") is None,
        """ Missing dependency `reged`. Install `chntpw` package first.
    See project page: https://pogostick.net/~pnh/ntpasswd/

    Ubuntu/Debian/Mint:
    $ sudo apt install chntpw
    """,
    )


def resolve_windows_location(user_selected_location: str | None, *, bot: bool = False) -> list[str]:
    if user_selected_location is not None:
        return [user_selected_location]

    win_locations = locate_windows_mount_points()
    how_many = len(win_locations)

    if how_many == 0:
        raise SystemExit(
            "ERROR: No Windows locations found!\n"
            "Make sure your Windows partition is mounted.\n"
            "  - List block devices: lsblk -f\n"
            "  - Mount manually: sudo mount /dev/sdXn /mnt/windows\n"
            "  - Or specify path: -w /mnt/windows"
        )

    if how_many == 1:
        return [win_locations[0]]

    # Multiple locations — interactive selection
    return _interactive_select_mount(win_locations, bot=bot)


def _interactive_select_mount(locations: list[str], *, bot: bool = False) -> list[str]:
    if bot or not sys.stdin.isatty():
        reason = "bot mode" if bot else "non-interactive mode"
        paths_list = "\n".join(f"  - {loc}" for loc in locations)
        raise SystemExit(
            f"ERROR: Multiple Windows locations found ({reason}):\n{paths_list}"
            "\nUse `-w MOUNT` to specify which one to use."
        )

    print("Multiple Windows locations found:")
    for i, loc in enumerate(locations, 1):
        print(f"  [{i}] {loc}")
    print()

    while True:
        raw = input("Select (e.g. 1 or 1,3 or all): ").strip().lower()
        if raw in ("all", "a"):
            return list(locations)

        indices = _parse_selection(raw, len(locations))
        if indices is not None:
            return [locations[i] for i in indices]

        print(f"Invalid selection. Enter numbers 1-{len(locations)}, comma-separated, or 'all'.")


def _parse_selection(raw: str, max_count: int) -> list[int] | None:
    """Parse user input like '1', '1,3', '1-3' into 0-based indices. Returns None on invalid input."""
    indices: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            range_parts = part.split("-", 1)
            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
            except ValueError:
                return None
            if start < 1 or end < 1 or start > end or end > max_count:
                return None
            indices.update(range(start - 1, end))
        else:
            try:
                n = int(part)
            except ValueError:
                return None
            if n < 1 or n > max_count:
                return None
            indices.add(n - 1)

    if not indices:
        return None

    return sorted(indices)


def print_header(caption: str) -> None:
    print()
    print(caption)
    print("=" * len(caption))


def _has_multiple_adapters(devices: list[BluetoothDevice] | None) -> bool:
    if devices is None:
        return False
    adapter_macs = {d.adapter_mac for d in devices}
    return len(adapter_macs) > 1


def print_devices_list(
    section_id: str,
    caption: str,
    devices: list[BluetoothDevice] | None,
    annotation: str | None = None,
    message_not_found: str | None = None,
    bot: bool = False,
) -> None:
    any_device = devices is not None and len(devices) > 0

    if bot is True:
        if any_device:
            assert devices is not None  # guaranteed by any_device check
            show_adapter = _has_multiple_adapters(devices)
            for device in devices:
                if show_adapter:
                    print(f"{section_id} {device.mac} {device.adapter_mac} {device.name}")
                else:
                    print(f"{section_id} {device.mac} {device.name}")
        else:
            print(f"{section_id} NONE")
        return

    if any_device or message_not_found is not None:
        print_header(caption)

        if any_device:
            assert devices is not None  # guaranteed by any_device check

            if annotation is not None:
                print()
                print(annotation)
                print()

            show_adapter = _has_multiple_adapters(devices)
            for device in devices:
                if show_adapter:
                    print(f" [{device.mac}] ({device.adapter_mac}) {device.name}")
                else:
                    print(f" [{device.mac}] {device.name}")
        elif message_not_found is not None:
            print()
            print(message_not_found)


class Application:
    def __init__(self, opts: argparse.Namespace) -> None:
        self.opts = opts
        self.__windows_path: str | None = None
        self.__windows_registry: WindowsRegistry | None = None
        self.__sync_service: SyncService | None = None

    def _opts_win_mount_point(self) -> str | None:
        mount_point = self.opts.win
        if mount_point is not None:
            mount_point = mount_point[0]

        if mount_point == "":
            mount_point = None

        return mount_point

    def _windows_path(self) -> str:
        assert self.__windows_path is not None, "Windows path not set — call _reset_windows_state first"
        return self.__windows_path

    def _windows_registry(self) -> WindowsRegistry:
        if self.__windows_registry is None:
            self.__windows_registry = WindowsRegistry(windows_path=self._windows_path())
        return self.__windows_registry

    def _sync_service(self) -> SyncService:
        if self.__sync_service is None:
            registry = self._windows_registry()
            linux_reader = LinuxDeviceReader()
            windows_reader = WindowsDeviceReader(registry)
            writer = WindowsDeviceWriter(registry)
            self.__sync_service = SyncService(linux_reader, windows_reader, writer)
        return self.__sync_service

    def is_dry_run(self) -> bool:
        return self.opts.dry_run is True

    def list_win_mounts(self) -> None:
        print_header("Windows locations:")
        for mount_point in locate_windows_mount_points():
            print(" " + mount_point)

    def list_devices(self) -> None:
        sync_service = self._sync_service()
        print_devices_list(
            "works",
            "Works both in Linux and Windows",
            devices=sync_service.devices_both_synced(),
            bot=self.opts.bot,
        )

        print_devices_list(
            "needs_sync",
            "Needs sync",
            devices=sync_service.devices_needs_sync(),
            annotation="Following devices available for sync with `--sync-all` or `--sync MAC` options.",
            message_not_found="No device found ready to sync.\nTry pair devices first.",
            bot=self.opts.bot,
        )

        print_devices_list(
            "missing_win",
            "Have to be paired in Windows",
            devices=sync_service.devices_absent_windows(),
            annotation="Following devices unavailable for sync unless you boot Windows and pair them",
            bot=self.opts.bot,
        )

        # Show devices without pairing key (unsyncable)
        print_devices_list(
            "missing_key",
            "Missing pairing key",
            devices=sync_service.devices_unsyncable(),
            annotation="Following devices do not have a pairing key and cannot be synced",
            bot=self.opts.bot,
        )

    def backup(self, path: str | bool, *, mount_suffix: str = "") -> None:
        if path is False:
            return
        backup_path: str = DEFAULT_BACKUP_PATH if path is True else path
        if mount_suffix:
            backup_path = os.path.join(backup_path, mount_suffix)

        saved_filename, restore_filename = self._windows_registry().backup(backup_path, dry_run=self.is_dry_run())
        heading = ["BACKUP"]

        if self.is_dry_run():
            heading.insert(0, "DRY RUN")

        print(f"> {' '.join(heading)} {restore_filename} to {saved_filename}")

    def sync_devices(self, macs: list[str]) -> None:
        with no_device_error_handler():
            self._sync_service().push(macs, dry_run=self.is_dry_run())
            status = "would be synced" if self.is_dry_run() else "synced"
            print(f"{status} {', '.join(macs)} successfully")

    def sync_all(self) -> None:
        sync_service = self._sync_service()
        with sync_service.no_cache():
            devices_for_push = sync_service.devices_needs_sync()

            if not devices_for_push:
                print("Nothing to sync")
                return

            with no_device_error_handler():
                print_devices_list(
                    "syncing",
                    "Syncing...",
                    devices=devices_for_push,
                    bot=self.opts.bot,
                )

                sync_service.push(devices_for_push, dry_run=self.is_dry_run())
                print("...done (dry run)" if self.is_dry_run() else "...done")

    def _has_sync_actions(self) -> bool:
        return self.opts.sync is not None or self.opts.sync_all is True

    def run(self) -> None:
        # --list-win-mounts is a diagnostic command, works without Windows/BT
        if self.opts.list_win_mounts:
            self.list_win_mounts()
            if not self.opts.list and not self._has_sync_actions():
                return

        # Resolve Windows location (needed for --list and sync actions)
        win_mounts = resolve_windows_location(self._opts_win_mount_point(), bot=self.opts.bot)

        # BT dir check: needed for both --list and sync, runs once before any action
        if self.opts.list or self._has_sync_actions():
            require_bt_dir_access()

        if self.opts.list:
            self._reset_windows_state(win_mounts[0])
            self.list_devices()

        # Sync loop: only when sync actions are requested
        if self._has_sync_actions():
            for i, mount in enumerate(win_mounts):
                if len(win_mounts) > 1:
                    print(f"\n{'=' * 40}")
                    print(f"[{i + 1}/{len(win_mounts)}] {mount}")
                    print("=" * 40)
                # Use mount point basename as suffix to avoid backup collisions
                mount_suffix = os.path.basename(mount) if len(win_mounts) > 1 else ""
                self._reset_windows_state(mount)
                self._run_sync_actions(mount_suffix=mount_suffix)

    def _reset_windows_state(self, mount: str) -> None:
        self.__windows_path = mount
        self.__windows_registry = None
        self.__sync_service = None

    def _run_sync_actions(self, *, mount_suffix: str = "") -> None:
        opt_backup = _opt_backup(self.opts.backup)
        if opt_backup is not None:
            self.backup(opt_backup, mount_suffix=mount_suffix)

        if self.opts.sync is not None:
            self.sync_devices(self.opts.sync)

        if self.opts.sync_all:
            self.sync_all()


def parse_argv() -> argparse.Namespace | None:
    parser = _argv_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        print()
        require_chntpw_package()
        return

    opts = parser.parse_args()

    if is_debug():
        print(f"argv: {opts}")

    if opts.version:
        print(f"{APP_NAME} {__version__}")
        return

    blank_states = {
        "list": False,
        "list_win_mounts": False,
        "sync_all": False,
        "sync": None,
    }

    opts_dict = vars(opts)

    required_specified = [name for name in blank_states if opts_dict[name] != blank_states[name]]

    if len(required_specified) == 0:
        parser.error("missing required argument")

    if opts.sync_all is True and opts.sync is not None:
        parser.error("`--sync-all` can't be used alongside with `--sync MAC`")

    opt_backup = _opt_backup(opts.backup)

    if opts.no_backup is True and opt_backup is not None:
        parser.error("`--backup` can't be used alongside with `--no-backup`")

    is_sync = opts.sync_all is True or opts.sync is not None
    is_backup_concern = opts.no_backup is True or opt_backup is not None

    if is_backup_concern and not is_sync:
        parser.error("--backup/--no-backup options makes sense only with --sync/--sync-all options")

    if is_sync and not is_backup_concern:
        msg = f"""Neither backup option given!

    Windows Registry Hive file will be updated!
    chntpw/reged tool is non-official and hackish Hive file editing tool.
    It is recommended to do backup prior writing into Hive file.

    Use:
      -b [path], --backup [path]    [default: {DEFAULT_BACKUP_PATH}]
      -n, --no-backup               process without backup

    WARNING:
        Windows Registry Hive file may contain sensitive data. You shouldn't keep this file
        on a storage which may be accessed by others. Consider to remove backup files as soon
        as possible after ensure Windows boots and works correctly.
"""
        parser.error(msg)

    return opts


def main() -> None:
    from .privilege import action_requires_root, elevate_via_sudo

    require_linux()
    opts = parse_argv()

    if opts is None:
        return

    if action_requires_root(opts) and not opts.no_elevate:
        elevate_via_sudo()

    require_chntpw_package()

    app = Application(opts)
    app.run()
