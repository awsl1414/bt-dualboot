import glob
import os

from bt_dualboot.domain.models import BluetoothDevice

from .parser import NotSyncableDeviceError, parse_device

_DEFAULT_BT_DIR = "/var/lib/bluetooth"


class LinuxDeviceReader:
    """Reads bluetooth devices from Linux filesystem."""

    def __init__(self, bt_dir: str = _DEFAULT_BT_DIR) -> None:
        self._bt_dir = bt_dir

    def read(self) -> list[BluetoothDevice]:
        """Return list of syncable devices (those with LinkKey or LongTermKey)."""
        syncable, _ = self.read_all()
        return syncable

    def read_all(self) -> tuple[list[BluetoothDevice], list[BluetoothDevice]]:
        """Return (syncable, unsyncable) device lists.

        Unsyncable devices have no LinkKey or LongTermKey in their info file.
        Devices are deduplicated by (mac, adapter_mac) — if both info and settings
        files exist for the same device, only the first successfully parsed entry is kept.
        """
        syncable: list[BluetoothDevice] = []
        unsyncable: list[BluetoothDevice] = []
        seen: set[tuple[str, str]] = set()

        for path in self._device_paths():
            is_syncable = True
            try:
                device = parse_device(path)
            except NotSyncableDeviceError:
                device = self._build_unsyncable_device(path)
                is_syncable = False

            identity = (device.mac, device.adapter_mac)
            if identity in seen:
                continue
            seen.add(identity)

            if is_syncable:
                syncable.append(device)
            else:
                unsyncable.append(device)

        return syncable, unsyncable

    def _device_paths(self) -> list[str]:
        info = glob.glob(os.path.join(self._bt_dir, "*", "*", "info"))
        settings = glob.glob(os.path.join(self._bt_dir, "*", "*", "settings"))
        return info + settings

    def _build_unsyncable_device(self, path: str) -> BluetoothDevice:
        """Build a minimal BluetoothDevice for a path that raised NotSyncableDeviceError."""
        import re
        from configparser import ConfigParser

        macs = re.search("([A-F0-9:]+)/([A-F0-9:]+)/(info|settings)$", path)
        if macs is None:
            raise NotSyncableDeviceError(f"{path}: cannot extract MAC addresses from path")

        mac = macs.group(2)
        adapter_mac = macs.group(1)

        name = None
        if path.endswith("info"):
            config = ConfigParser()
            config.read(path)
            name = config.get("General", "Name", fallback=None)

        return BluetoothDevice(mac=mac, name=name, adapter_mac=adapter_mac)
