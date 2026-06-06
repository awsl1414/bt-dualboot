import sys
from collections.abc import Generator
from contextlib import contextmanager

# fmt: off
from bt_dualboot.bt_linux.devices import get_devices as get_linux_devices
from bt_dualboot.bt_windows.convert import (
    hex_string_to_reg_value,
    int_to_dword_reg_value,
    int_to_qword_reg_value,
    mac_to_reg_key,
)
from bt_dualboot.bt_windows.devices import get_devices as get_windows_devices
from bt_dualboot.models.bluetooth_device import BluetoothDevice
from bt_dualboot.windows_registry import WindowsRegistry

# fmt: on

type DeviceOrMac = str | BluetoothDevice
type DeviceOrMacList = DeviceOrMac | list[str] | list[BluetoothDevice]


class DeviceNotFoundError(Exception):
    pass


class BtSyncManager:
    """Provides service for syncing of bluetooth pairing keys between Linux and Windows

    Terms:
        push: write pairing keys from Linux to Windows
        pull: write pairing keys from Windows to Linx (not implemented, out of scope of this tool)
    """

    def __init__(self, windows_registry: WindowsRegistry) -> None:
        self.windows_registry = windows_registry
        self.index_cache: dict[str, list[BluetoothDevice]] | None = None

    def flush_cache(self) -> None:
        self.index_cache = None

    @contextmanager
    def no_cache(self) -> Generator[None]:
        """
        Usage:
            with sync_manager.no_cache():
                pass
        """
        self.flush_cache()
        yield
        self.flush_cache()

    def _index_devices(self) -> dict[str, list[BluetoothDevice]]:
        """
        Indexes and chache BluetoothDevice lists both from Linux and Windows

        !cached

        NOTE: this index used to match Windows and Linux devices prior copy&update data

        Returns:
            dict[MAC, list[BluetoothDevice]]:
                key: device MAC
                value: (linux_device, windows_device) pair of BluetoothDevice instances
        """
        if self.index_cache is not None:
            return self.index_cache

        index: dict[str, list[BluetoothDevice]] = {}

        # fmt: off
        linux_devices   = get_linux_devices()
        windows_devices = get_windows_devices(self.windows_registry)
        # fmt: on

        for device in linux_devices:
            if device.mac not in index:
                index[device.mac] = []
            index[device.mac].append(device)

        problem_devices_macs = [mac for mac, devices in index.items() if len(devices) > 1]

        if len(problem_devices_macs) > 0:
            # fmt: off
            print(
                f"WARNING: Following devices paired on Linux for multiple BT-adapters: {', '.join(problem_devices_macs)}",
                file=sys.stderr
            )
            # fmt: on

        for device in windows_devices:
            if device.mac not in index:
                index[device.mac] = []
            index[device.mac].append(device)

        problem_devices_macs = [mac for mac, devices in index.items() if len(devices) > 2]

        if len(problem_devices_macs) > 0:
            # fmt: off
            print(
                f"WARNING: Following devices paired on Windows for multiple BT-adapters: {', '.join(problem_devices_macs)}",
                file=sys.stderr
            )
            # fmt: on

        self.index_cache = index
        return self.index_cache

    def _get_reg_adapter_section_key(self, device: BluetoothDevice) -> str:
        return r"ControlSet001\Services\BTHPORT\Parameters\Keys" + "\\" + mac_to_reg_key(device.adapter_mac)

    def _get_reg_device_section_key(self, device: BluetoothDevice) -> str:
        return self._get_reg_adapter_section_key(device) + "\\" + mac_to_reg_key(device.mac)

    def devices_both_synced(self) -> list[BluetoothDevice]:
        """
        !uses cached

        Returns:
            list[BluetoothDevice]: which have the same pairing_key for Linux and Windows
        """

        index = self._index_devices()

        common_devices_macs = [mac for mac, devices in index.items() if len(devices) == 2]
        synced_devices = [
            index[mac][0]
            for mac in common_devices_macs
            if index[mac][0].pairing_fingerprint() == index[mac][1].pairing_fingerprint()
        ]

        return synced_devices

    def devices_needs_sync(self) -> list[BluetoothDevice]:
        """
        !uses cached

        Returns:
            list[BluetoothDevice]: which exist both in Linux and Windows, but have different pairing keys
        """
        index = self._index_devices()

        common_devices_macs = [mac for mac, devices in index.items() if len(devices) == 2]
        needs_sync_devices = [
            index[mac][0]
            for mac in common_devices_macs
            if index[mac][0].pairing_fingerprint() != index[mac][1].pairing_fingerprint()
        ]

        return needs_sync_devices

    def devices_absent_windows(self) -> list[BluetoothDevice]:
        """
        !uses cached

        Returns:
            list[BluetoothDevice]: which exist both in Linux and Windows, but have different pairing keys
        """

        index = self._index_devices()
        single_linux_devices = [
            devices[0] for mac, devices in index.items() if len(devices) == 1 and devices[0].is_source_linux()
        ]
        return single_linux_devices

    def _param_get_macs_list(self, device_or_mac_or_list: DeviceOrMacList) -> list[str]:
        """Align plural argument to list of devices MACs

        Args:
            device_or_mac_or_list: str, BluetoothDevice, or list of either

        Returns:
            list[str]: list of devices MACs like ["B6:C2:D3:E5:F2:0D", ...]
        """
        # handling: type|list<type> pluralism
        target_items_dirty = device_or_mac_or_list
        if not isinstance(target_items_dirty, list):
            target_items_dirty = [target_items_dirty]

        # handling: list<str>|list<BluetoothDevice> pluralism
        target_items_macs: list[str] = []
        for item in target_items_dirty:
            if isinstance(item, BluetoothDevice):
                target_items_macs.append(item.mac)
            else:
                target_items_macs.append(item)

        return target_items_macs

    def _update_windows_registry(self, devices: list[BluetoothDevice]) -> None:
        """Performs Windows registry import for given devices

        !updates Windows Hive file

        Args:
            devices: list of BluetoothDevice for import
        """
        for_import: dict[str, dict[str, str]] = {}
        for device in devices:
            if device.is_pairing_type_long_term_key():
                section_key = self._get_reg_device_section_key(device)
                section_data: dict[str, str] = {
                    '"LTK"': hex_string_to_reg_value(device.pairing_data["Key"]),
                    '"KeyLength"': int_to_dword_reg_value(device.pairing_data.get("EncSize", 16)),
                    '"EDIV"': int_to_dword_reg_value(device.pairing_data.get("EDiv", 0)),
                    '"ERand"': int_to_qword_reg_value(device.pairing_data.get("Rand", 0)),
                }
                optional_key_map: dict[str, str] = {
                    "IRK": '"IRK"',
                    "CSRK": '"CSRK"',
                    "CSRKInbound": '"CSRKInbound"',
                }
                for data_key, registry_key in optional_key_map.items():
                    if data_key in device.pairing_data:
                        section_data[registry_key] = hex_string_to_reg_value(device.pairing_data[data_key])
                for_import[section_key] = section_data
            else:
                section_key = self._get_reg_adapter_section_key(device)
                device_key = f'"{mac_to_reg_key(device.mac)}"'
                pairing_key = hex_string_to_reg_value(device.pairing_key)
                for_import[section_key] = {device_key: pairing_key}

        self.windows_registry.import_dict(for_import)

    def push(self, device_or_mac_or_list: DeviceOrMacList, dry_run: bool = False) -> None:
        """Copy pairing keys from Linux to Windows, import updates into Windows registry

        !updates Windows Hive file

        Args:
            device_or_mac_or_list: str, BluetoothDevice, or list of either

        Raises:
            DeviceNotFoundError
        """
        target_items_macs = self._param_get_macs_list(device_or_mac_or_list)

        with self.no_cache():
            index = self._index_devices()

            needs_sync_macs = [device.mac for device in self.devices_needs_sync()]
            absent_in_needs_sync = set(target_items_macs) - set(needs_sync_macs)
            if len(absent_in_needs_sync) > 0:
                macs_msg = ", ".join(list(absent_in_needs_sync))
                raise DeviceNotFoundError(f"Can't push {macs_msg}! Not found or already in sync!")

            devices_for_update: list[BluetoothDevice] = []
            for device_mac in target_items_macs:
                if device_mac not in index:
                    raise DeviceNotFoundError(f"Can't push {device_mac}! Not found!")

                linux_devices = [d for d in index[device_mac] if d.is_source_linux()]
                windows_devices = [d for d in index[device_mac] if d.is_source_windows()]

                if not linux_devices:
                    raise DeviceNotFoundError(f"Can't push {device_mac}! Not found on Linux!")

                if not windows_devices:
                    raise DeviceNotFoundError(f"Can't push {device_mac}! Not found on Windows!")

                device_linux = linux_devices[0]
                device_windows = windows_devices[0]

                device_windows.pairing_key = device_linux.pairing_key
                device_windows.pairing_type = device_linux.pairing_type
                device_windows.pairing_data = dict(device_linux.pairing_data)
                devices_for_update.append(device_windows)

            if dry_run is not True:
                self._update_windows_registry(devices_for_update)
            else:
                print(f"> DRY RUN: push devices {', '.join([device.mac for device in devices_for_update])}")
