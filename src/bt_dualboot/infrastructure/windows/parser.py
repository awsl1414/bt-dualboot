import re

from .convert import _unquote, mac_from_reg_key

REG_KEY__BLUETOOTH_PAIRING_KEYS: str = r"ControlSet001\Services\BTHPORT\Parameters\Keys"

# Default values for BLE LongTermKey fields when missing from registry
_DEFAULT_ENC_SIZE = "dword:00000010"
_DEFAULT_EDIV = "dword:00000000"
_DEFAULT_ERAND = "hex(b):00,00,00,00,00,00,00,00"


def extract_adapter_mac(from_section_key: str) -> str | None:
    """Extracts adapter MAC from section key"""
    res = re.search("Services.BTHPORT.Parameters.Keys.([a-f0-9]+)$", from_section_key)
    if res is None:
        return None

    return mac_from_reg_key(res.groups()[0])


def extract_adapter_and_device_mac(from_section_key: str) -> dict[str, str] | None:
    """Extracts adapter and BLE device MACs from a Windows registry section key."""
    res = re.search(r"Services.BTHPORT.Parameters.Keys.([a-f0-9]+).([a-f0-9]+)$", from_section_key)
    if res is None:
        return None

    adapter_mac, device_mac = res.groups()
    return {
        "adapter_mac": mac_from_reg_key(adapter_mac),
        "device_mac": mac_from_reg_key(device_mac),
    }


def _section_dict(section: dict[str, str]) -> dict[str, str]:
    """Convert registry section to lowercase unquoted key dict for lookup."""
    return {_unquote(key).lower(): value for key, value in section.items()}
