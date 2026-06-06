import re
from configparser import ConfigParser

from bt_dualboot.domain.enums import DeviceSource, PairingType
from bt_dualboot.domain.models import BluetoothDevice

# Default values for BLE LongTermKey fields
_DEFAULT_ENC_SIZE = "16"
_DEFAULT_EDIV = "0"
_DEFAULT_RAND = "0"


class NotSyncableDeviceError(Exception):
    pass


def extract_macs(device_info_path: str) -> dict[str, str] | None:
    """Extracts adapter and device MAC from path to /info or /settings file

    Args:
        device_info_path: Kind of .../foo/A4:6B:6C:9D:E2:FB/B6:C2:D3:E5:F2:0D/info
                          or   .../foo/A4:6B:6C:9D:E2:FB/44:16:22:E6:73:15/settings

    Returns:
        dict: Kind of { device_mac: <device MAC>, adapter_mac: <adapter MAC> }
    """
    match = re.search("([A-F0-9:]+)/([A-F0-9:]+)/(info|settings)$", device_info_path)
    if match is None:
        return None

    adapter_mac, device_mac, _ = match.groups()
    return {"device_mac": device_mac, "adapter_mac": adapter_mac}


def _long_term_key_section(config: ConfigParser) -> str | None:
    """Find the first available LongTermKey section in config.

    Checks LongTermKey, PeripheralLongTermKey, SlaveLongTermKey in order.
    """
    for section in ["LongTermKey", "PeripheralLongTermKey", "SlaveLongTermKey"]:
        if config.get(section, "Key", fallback=None) is not None:
            return section

    return None


def extract_info(device_info_path: str) -> dict[str, str | None | dict[str, str]]:
    """Extracts adapter info from Linux /path/to/info

    Args:
        device_info_path: Kind of .../foo/A4:6B:6C:9D:E2:FB/B6:C2:D3:E5:F2:0D/info

    Returns:
        dict: Kind of { name:, class:, pairing_key:, pairing_type:, pairing_data: }
    """
    config = ConfigParser()
    config.read(device_info_path)

    link_key = config.get("LinkKey", "Key", fallback=None)
    long_term_key_section = _long_term_key_section(config)
    long_term_key = None
    if long_term_key_section is not None:
        long_term_key = config.get(long_term_key_section, "Key")

    pairing_type: str | None = None
    pairing_key: str | None = None
    pairing_data: dict[str, str] = {}

    if link_key is not None:
        pairing_type = PairingType.LINK_KEY
        pairing_key = link_key
        pairing_data = {"Key": link_key}
    elif long_term_key is not None:
        pairing_type = PairingType.LONG_TERM_KEY
        pairing_key = long_term_key
        pairing_data = {
            "Key": long_term_key,
            "EncSize": config.get(long_term_key_section, "EncSize", fallback=_DEFAULT_ENC_SIZE),
            "EDiv": config.get(long_term_key_section, "EDiv", fallback=_DEFAULT_EDIV),
            "Rand": config.get(long_term_key_section, "Rand", fallback=_DEFAULT_RAND),
        }
        optional_key_map: dict[str, tuple[str, str]] = {
            "IRK": ("IdentityResolvingKey", "Key"),
            "CSRK": ("LocalSignatureKey", "Key"),
            "CSRKInbound": ("RemoteSignatureKey", "Key"),
        }
        for data_key, section_option in optional_key_map.items():
            section, option = section_option
            value = config.get(section, option, fallback=None)
            if value is not None:
                pairing_data[data_key] = value

    return {
        "name": config.get("General", "Name", fallback=None),
        "class": config.get("General", "Class", fallback=None),
        "pairing_key": pairing_key,
        "pairing_type": pairing_type,
        "pairing_data": pairing_data,
    }


def parse_device(device_info_path: str) -> BluetoothDevice:
    """Build BluetoothDevice instance for given /path/to/info

    Args:
        device_info_path: Kind of .../foo/A4:6B:6C:9D:E2:FB/B6:C2:D3:E5:F2:0D/info

    Returns:
        BluetoothDevice

    Raises:
        NotSyncableDeviceError: when device has no LinkKey or LongTermKey
    """
    macs = extract_macs(device_info_path)
    info = extract_info(device_info_path)

    if info["pairing_key"] is None:
        raise NotSyncableDeviceError(
            f"{device_info_path} has no LinkKey or LongTermKey; device is not syncable by this tool"
        )

    return BluetoothDevice(
        source=DeviceSource.LINUX,
        klass=info["class"],
        mac=macs["device_mac"],
        name=info["name"],
        pairing_key=info["pairing_key"],
        adapter_mac=macs["adapter_mac"],
        pairing_type=info["pairing_type"],
        pairing_data=info["pairing_data"],
    )
