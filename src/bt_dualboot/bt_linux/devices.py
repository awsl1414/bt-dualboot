import glob
import os
from contextlib import suppress

from bt_dualboot.models.bluetooth_device import BluetoothDevice

from .bluetooth_device_factory import NotSyncableDeviceError, bluetooth_device_factory

LINUX_BT_DIR: str = "/var/lib/bluetooth"


def get_adapters_macs() -> list[str]:
    """Lists available bluetooths adapeters

    Returns:
        list[str]: kind of ['A4:6B:6C:9D:E2:FB', ...]
    """
    return os.listdir(LINUX_BT_DIR)


def get_adapters_paths() -> list[str]:
    """Lists paths to available bluetooths adapters

    Returns:
        list[str]: kind of ['/var/lib/bluetooths/A4:6B:6C:9D:E2:FB', ...]
    """
    return [os.path.join(LINUX_BT_DIR, dir_name) for dir_name in os.listdir(LINUX_BT_DIR)]


def get_devices_paths() -> list[str]:
    """Lists paths to available bluetooths devices

    Returns:
        list[str]: kind of ['/var/lib/bluetooths/A4:6B:6C:9D:E2:FB/B4:6B:6C:9D:E2:FB/info', ...]
    """
    info_paths = glob.glob(os.path.join(LINUX_BT_DIR, "*", "*", "info"))
    settings_paths = glob.glob(os.path.join(LINUX_BT_DIR, "*", "*", "settings"))
    return info_paths + settings_paths


def get_devices() -> list[BluetoothDevice]:
    """
    Returns:
        list[BluetoothDevice]: linux registred bluetooths devices
    """
    devices: list[BluetoothDevice] = []
    for device_path in get_devices_paths():
        with suppress(NotSyncableDeviceError):
            devices.append(bluetooth_device_factory(device_path))

    return devices
