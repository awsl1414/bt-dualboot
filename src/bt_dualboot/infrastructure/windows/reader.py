from bt_dualboot.domain.enums import DeviceSource, PairingType
from bt_dualboot.domain.models import BluetoothDevice
from bt_dualboot.infrastructure.registry.hive import WindowsRegistry

from .convert import hex_string_from_reg, int_from_le_reg_value, is_mac_reg_key, mac_from_reg_key
from .parser import (
    _DEFAULT_EDIV,
    _DEFAULT_ENC_SIZE,
    _DEFAULT_ERAND,
    REG_KEY__BLUETOOTH_PAIRING_KEYS,
    _section_dict,
    extract_adapter_and_device_mac,
    extract_adapter_mac,
)


class WindowsDeviceReader:
    """Reads bluetooth devices from Windows registry."""

    def __init__(self, registry: WindowsRegistry) -> None:
        self._registry = registry

    def read(self) -> list[BluetoothDevice]:
        reg_data = self._registry.export_as_config(REG_KEY__BLUETOOTH_PAIRING_KEYS)

        bluetooth_devices: list[BluetoothDevice] = []
        for section_key in reg_data:
            adapter_mac = extract_adapter_mac(section_key)
            if adapter_mac is None:
                device = self._parse_ble_device(section_key, reg_data[section_key])
                if device is not None:
                    bluetooth_devices.append(device)
                continue

            for device_mac_raw, pairing_key_raw in reg_data[section_key].items():
                if not is_mac_reg_key(device_mac_raw):
                    continue

                pairing_key = hex_string_from_reg(pairing_key_raw)
                bluetooth_devices.append(
                    BluetoothDevice(
                        source=DeviceSource.WINDOWS,
                        mac=mac_from_reg_key(device_mac_raw),
                        adapter_mac=adapter_mac,
                        pairing_key=pairing_key,
                        pairing_type=PairingType.LINK_KEY,
                        pairing_data={"Key": pairing_key},
                    )
                )

        return bluetooth_devices

    def _parse_ble_device(self, section_key: str, section_data: dict[str, str]) -> BluetoothDevice | None:
        macs = extract_adapter_and_device_mac(section_key)
        if macs is None:
            return None

        section = _section_dict(section_data)
        if "ltk" not in section:
            return None

        pairing_data: dict[str, str] = {
            "Key": hex_string_from_reg(section["ltk"]),
            "EncSize": str(int_from_le_reg_value(section.get("keylength", _DEFAULT_ENC_SIZE))),
            "EDiv": str(int_from_le_reg_value(section.get("ediv", _DEFAULT_EDIV))),
            "Rand": str(int_from_le_reg_value(section.get("erand", _DEFAULT_ERAND))),
        }
        optional_key_map: dict[str, str] = {
            "IRK": "irk",
            "CSRK": "csrk",
            "CSRKInbound": "csrkinbound",
        }
        for data_key, registry_key in optional_key_map.items():
            if registry_key in section:
                pairing_data[data_key] = hex_string_from_reg(section[registry_key])

        return BluetoothDevice(
            source=DeviceSource.WINDOWS,
            mac=macs["device_mac"],
            adapter_mac=macs["adapter_mac"],
            pairing_key=pairing_data["Key"],
            pairing_type=PairingType.LONG_TERM_KEY,
            pairing_data=pairing_data,
        )
