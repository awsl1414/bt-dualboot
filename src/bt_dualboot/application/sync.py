import dataclasses
from collections.abc import Generator
from contextlib import contextmanager

from bt_dualboot.domain.enums import DeviceSource
from bt_dualboot.domain.models import BluetoothDevice
from bt_dualboot.domain.protocols import DeviceReader, DeviceWriter

type DeviceOrMac = str | BluetoothDevice
type DeviceOrMacList = DeviceOrMac | list[str] | list[BluetoothDevice]


class DeviceNotFoundError(Exception):
    pass


class SyncService:
    """Provides service for syncing of bluetooth pairing keys between Linux and Windows

    Terms:
        push: write pairing keys from Linux to Windows
        pull: write pairing keys from Windows to Linux (not implemented, out of scope)
    """

    def __init__(
        self,
        linux_reader: DeviceReader,
        windows_reader: DeviceReader,
        windows_writer: DeviceWriter,
    ) -> None:
        self._linux_reader = linux_reader
        self._windows_reader = windows_reader
        self._windows_writer = windows_writer
        self._index_cache: dict[str, list[BluetoothDevice]] | None = None

    def flush_cache(self) -> None:
        self._index_cache = None

    @contextmanager
    def no_cache(self) -> Generator[None]:
        self.flush_cache()
        yield
        self.flush_cache()

    def _index_devices(self) -> dict[str, list[BluetoothDevice]]:
        """Indexes and caches BluetoothDevice lists from Linux and Windows"""
        if self._index_cache is not None:
            return self._index_cache

        index: dict[str, list[BluetoothDevice]] = {}

        for device in self._linux_reader.read():
            index.setdefault(device.mac, []).append(device)

        for device in self._windows_reader.read():
            index.setdefault(device.mac, []).append(device)

        self._index_cache = index
        return self._index_cache

    def devices_both_synced(self) -> list[BluetoothDevice]:
        """Returns devices which have the same pairing_key for Linux and Windows"""
        index = self._index_devices()

        common_devices_macs = [mac for mac, devices in index.items() if len(devices) == 2]
        return [
            index[mac][0]
            for mac in common_devices_macs
            if index[mac][0].pairing_fingerprint() == index[mac][1].pairing_fingerprint()
        ]

    def devices_needs_sync(self) -> list[BluetoothDevice]:
        """Returns devices which exist both in Linux and Windows, but have different pairing keys"""
        index = self._index_devices()

        common_devices_macs = [mac for mac, devices in index.items() if len(devices) == 2]
        return [
            index[mac][0]
            for mac in common_devices_macs
            if index[mac][0].pairing_fingerprint() != index[mac][1].pairing_fingerprint()
        ]

    def devices_absent_windows(self) -> list[BluetoothDevice]:
        """Returns devices which exist only in Linux"""
        index = self._index_devices()
        return [
            devices[0]
            for mac, devices in index.items()
            if len(devices) == 1 and devices[0].source == DeviceSource.LINUX
        ]

    def _param_get_macs_list(self, device_or_mac_or_list: DeviceOrMacList) -> list[str]:
        """Align plural argument to list of devices MACs"""
        target_items_dirty = device_or_mac_or_list
        if not isinstance(target_items_dirty, list):
            target_items_dirty = [target_items_dirty]

        target_items_macs: list[str] = []
        for item in target_items_dirty:
            if isinstance(item, BluetoothDevice):
                target_items_macs.append(item.mac)
            else:
                target_items_macs.append(item)

        return target_items_macs

    def push(self, target: DeviceOrMacList, *, dry_run: bool = False) -> None:
        """Copy pairing keys from Linux to Windows, import updates into Windows registry

        Raises:
            DeviceNotFoundError
        """
        target_items_macs = self._param_get_macs_list(target)

        with self.no_cache():
            index = self._index_devices()

            needs_sync_macs = [device.mac for device in self.devices_needs_sync()]
            absent_in_needs_sync = set(target_items_macs) - set(needs_sync_macs)
            if absent_in_needs_sync:
                macs_msg = ", ".join(list(absent_in_needs_sync))
                raise DeviceNotFoundError(f"Can't push {macs_msg}! Not found or already in sync!")

            devices_for_update: list[BluetoothDevice] = []
            for device_mac in target_items_macs:
                if device_mac not in index:
                    raise DeviceNotFoundError(f"Can't push {device_mac}! Not found!")

                linux_devices = [d for d in index[device_mac] if d.source == DeviceSource.LINUX]
                windows_devices = [d for d in index[device_mac] if d.source == DeviceSource.WINDOWS]

                if not linux_devices:
                    raise DeviceNotFoundError(f"Can't push {device_mac}! Not found on Linux!")

                if not windows_devices:
                    raise DeviceNotFoundError(f"Can't push {device_mac}! Not found on Windows!")

                device_linux = linux_devices[0]
                device_windows = windows_devices[0]

                updated = dataclasses.replace(
                    device_windows,
                    pairing_key=device_linux.pairing_key,
                    pairing_type=device_linux.pairing_type,
                    pairing_data=dict(device_linux.pairing_data),
                )
                devices_for_update.append(updated)

            if not dry_run:
                self._windows_writer.write_devices(devices_for_update)
