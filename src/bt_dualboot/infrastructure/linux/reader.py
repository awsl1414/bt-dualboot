import glob
import os
from contextlib import suppress

from bt_dualboot.domain.models import BluetoothDevice

from .parser import NotSyncableDeviceError, parse_device

_DEFAULT_BT_DIR = "/var/lib/bluetooth"


class LinuxDeviceReader:
    """Reads bluetooth devices from Linux filesystem."""

    def __init__(self, bt_dir: str = _DEFAULT_BT_DIR) -> None:
        self._bt_dir = bt_dir

    def read(self) -> list[BluetoothDevice]:
        paths = self._device_paths()
        devices = []
        for path in paths:
            with suppress(NotSyncableDeviceError):
                devices.append(parse_device(path))
        return devices

    def _device_paths(self) -> list[str]:
        info = glob.glob(os.path.join(self._bt_dir, "*", "*", "info"))
        settings = glob.glob(os.path.join(self._bt_dir, "*", "*", "settings"))
        return info + settings
