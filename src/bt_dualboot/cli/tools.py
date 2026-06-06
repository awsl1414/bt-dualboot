import os
import shutil
import sys
from itertools import repeat

from bt_dualboot.bt_linux.devices import LINUX_BT_DIR, get_devices_paths
from bt_dualboot.models.bluetooth_device import BluetoothDevice
from bt_dualboot.win_mount import locate_windows_mount_points


def is_debug() -> bool:
    return os.environ.get("DEBUG") == "1"


def is_linux() -> bool:
    return sys.platform.find("linux") == 0


def invariant_and_halt(condition: bool, error_message: str) -> None:
    if condition:
        raise SystemExit(f"ERROR: {error_message}")


def require_linux() -> None:
    invariant_and_halt(not is_linux(), "Intended to be used only from Linux.")


def require_bt_dir_access() -> None:
    invariant_and_halt(
        len(get_devices_paths()) == 0,
        f"No Bluetooth devices found!\nCheck if your user have access to {LINUX_BT_DIR} and at least one device paired. Try use sudo.",
    )


def require_chntpw_package() -> None:
    invariant_and_halt(
        shutil.which("reged") is None,
        """ Missing dependency `reged`. Install `chntpw` package first.
    See project page: https://pogostick.net/~pnh/ntpasswd/

    Ubuntu/Debian/Mint:
    $ sudo apt install chntpw
    """,
    )


def require_univocal_windows_location(user_selected_location: str | None) -> None:
    """
    Raises:
        SystemExit: when no Windows location found or locations is ambigous
    """

    if user_selected_location is not None:
        return

    win_locations = locate_windows_mount_points()
    how_much = len(win_locations)
    if how_much == 0:
        how_much = "None"

    invariant_and_halt(
        len(win_locations) != 1,
        f"{how_much} Windows locations found, use `--win MOUNT` to point actual Windows location",
    )


def print_header(caption: str) -> None:
    """
    Prints:
        Underlined header
        =================
    """
    print()
    print(caption)
    print("".join(repeat("=", len(caption))))


def print_devices_list(
    section_id: str,
    caption: str,
    devices: list[BluetoothDevice] | None,
    annotation: str | None = None,
    message_not_found: str | None = None,
    bot: bool = False,
) -> None:
    """Prints devices list with caption and annotation or not found fallaback message

    Args:
        section_id: unique string for bot=True, delimeter characteres not allowed
        caption: header text
        devices: list of BluetoothDevice instances
        annotation: optional annotation text
        message_not_found: optional fallback message
        bot: format parsable output for robots
    """
    any_device = devices is not None and len(devices) > 0

    if bot is True:
        if any_device:
            for device in devices:
                print(f"{section_id} {device.mac} {device.name}")
        else:
            print(f"{section_id} NONE")
        return

    if any_device or message_not_found is not None:
        print_header(caption)

        if any_device:
            if annotation is not None:
                print()
                print(annotation)
                print()

            for device in devices:
                print(f" [{device.mac}] {device.name}")
            pass
        elif message_not_found is not None:
            print()
            print(message_not_found)
