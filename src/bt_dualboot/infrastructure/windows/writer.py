from bt_dualboot.domain.models import BluetoothDevice
from bt_dualboot.infrastructure.registry.hive import WindowsRegistry

from .convert import hex_string_to_reg_value, int_to_dword_reg_value, int_to_qword_reg_value, mac_to_reg_key
from .parser import REG_KEY__BLUETOOTH_PAIRING_KEYS


class WindowsDeviceWriter:
    """Writes bluetooth pairing keys into Windows registry."""

    def __init__(self, registry: WindowsRegistry) -> None:
        self._registry = registry

    def write_devices(self, devices: list[BluetoothDevice]) -> None:
        import_data = self._build_import_dict(devices)
        self._registry.import_dict(import_data)

    def _build_import_dict(self, devices: list[BluetoothDevice]) -> dict[str, dict[str, str]]:
        for_import: dict[str, dict[str, str]] = {}
        for device in devices:
            if device.is_pairing_type_long_term_key():
                for_import[self._reg_device_section_key(device)] = self._build_ltk_section(device)
            else:
                section_key = self._reg_adapter_section_key(device)
                device_entry = self._build_classic_section(device)
                if section_key in for_import:
                    for_import[section_key].update(device_entry)
                else:
                    for_import[section_key] = device_entry
        return for_import

    def _build_ltk_section(self, device: BluetoothDevice) -> dict[str, str]:
        section_data: dict[str, str] = {
            '"LTK"': hex_string_to_reg_value(device.pairing_data["Key"]),
            '"KeyLength"': int_to_dword_reg_value(device.pairing_data.get("EncSize", "16")),
            '"EDIV"': int_to_dword_reg_value(device.pairing_data.get("EDiv", "0")),
            '"ERand"': int_to_qword_reg_value(device.pairing_data.get("Rand", "0")),
        }
        optional_key_map: dict[str, str] = {
            "IRK": '"IRK"',
            "CSRK": '"CSRK"',
            "CSRKInbound": '"CSRKInbound"',
        }
        for data_key, registry_key in optional_key_map.items():
            if data_key in device.pairing_data:
                section_data[registry_key] = hex_string_to_reg_value(device.pairing_data[data_key])
        return section_data

    def _build_classic_section(self, device: BluetoothDevice) -> dict[str, str]:
        device_key = f'"{mac_to_reg_key(device.mac)}"'
        pairing_key = hex_string_to_reg_value(device.pairing_key)
        return {device_key: pairing_key}

    def _reg_adapter_section_key(self, device: BluetoothDevice) -> str:
        return REG_KEY__BLUETOOTH_PAIRING_KEYS + "\\" + mac_to_reg_key(device.adapter_mac)

    def _reg_device_section_key(self, device: BluetoothDevice) -> str:
        return self._reg_adapter_section_key(device) + "\\" + mac_to_reg_key(device.mac)
