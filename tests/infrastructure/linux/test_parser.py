import os

from bt_dualboot.domain.enums import DeviceSource, PairingType
from bt_dualboot.infrastructure.linux.parser import (
    extract_info,
    extract_macs,
    parse_device,
)

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_samples")
SMPL_BT_SAMPLE_01 = os.path.join(SAMPLES_DIR, "bt_sample_01")
SAMPLE_DEVICE_INFO_PATH = os.path.join(SMPL_BT_SAMPLE_01, "A4:6B:6C:9D:E2:FB", "B6:C2:D3:E5:F2:0D", "info")
SAMPLE_BLE_DEVICE_INFO_PATH = os.path.join(SMPL_BT_SAMPLE_01, "A4:6B:6C:9D:E2:FB", "AA:BB:CC:DD:EE:FF", "info")
SAMPLE_BLE_DEVICE_SETTINGS_PATH = os.path.join(SMPL_BT_SAMPLE_01, "A4:6B:6C:9D:E2:FB", "44:16:22:E6:73:15", "settings")


def test_extract_macs():
    expected = {"device_mac": "B6:C2:D3:E5:F2:0D", "adapter_mac": "A4:6B:6C:9D:E2:FB"}
    assert extract_macs(SAMPLE_DEVICE_INFO_PATH) == expected


def test_extract_macs__settings():
    expected = {"device_mac": "44:16:22:E6:73:15", "adapter_mac": "A4:6B:6C:9D:E2:FB"}
    assert extract_macs(SAMPLE_BLE_DEVICE_SETTINGS_PATH) == expected


def test_extract_info():
    expected = {
        "name": "DEV-1-02-Name",
        "class": "0x000540",
        "pairing_key": "A515CBE4E8F2E236FF999C0A53369EF6",
        "pairing_type": "LinkKey",
        "pairing_data": {"Key": "A515CBE4E8F2E236FF999C0A53369EF6"},
    }
    assert extract_info(SAMPLE_DEVICE_INFO_PATH) == expected


def test_extract_info__with_long_term_key():
    expected = {
        "name": "BLE Device Without LinkKey",
        "class": None,
        "pairing_key": "FFEEDDCCBBAA99887766554433221100",
        "pairing_type": "LongTermKey",
        "pairing_data": {
            "Key": "FFEEDDCCBBAA99887766554433221100",
            "EncSize": "16",
            "EDiv": "4660",
            "Rand": "72623859790382856",
            "IRK": "00112233445566778899AABBCCDDEEFF",
        },
    }
    assert extract_info(SAMPLE_BLE_DEVICE_INFO_PATH) == expected


def test_parse_device():
    device = parse_device(SAMPLE_DEVICE_INFO_PATH)

    assert device.__class__.__name__ == "BluetoothDevice"
    assert device.klass == "0x000540"
    assert device.mac == "B6:C2:D3:E5:F2:0D"
    assert device.name == "DEV-1-02-Name"
    assert device.pairing_key == "A515CBE4E8F2E236FF999C0A53369EF6"
    assert device.pairing_type == "LinkKey"
    assert device.source == DeviceSource.LINUX


def test_parse_device__with_long_term_key():
    device = parse_device(SAMPLE_BLE_DEVICE_INFO_PATH)

    assert device.__class__.__name__ == "BluetoothDevice"
    assert device.mac == "AA:BB:CC:DD:EE:FF"
    assert device.name == "BLE Device Without LinkKey"
    assert device.pairing_key == "FFEEDDCCBBAA99887766554433221100"
    assert device.pairing_type == PairingType.LONG_TERM_KEY
    assert device.source == DeviceSource.LINUX


def test_parse_device__with_peripheral_long_term_key_settings():
    device = parse_device(SAMPLE_BLE_DEVICE_SETTINGS_PATH)

    assert device.__class__.__name__ == "BluetoothDevice"
    assert device.mac == "44:16:22:E6:73:15"
    assert device.name == "Xbox Wireless Controller"
    assert device.pairing_key == "17A15A0C831234C6ABA9E34A1363ED10"
    assert device.pairing_type == PairingType.LONG_TERM_KEY
    assert device.pairing_data == {
        "Key": "17A15A0C831234C6ABA9E34A1363ED10",
        "EncSize": "16",
        "EDiv": "0",
        "Rand": "0",
        "IRK": "76371573E622164443DAEAEBCCED3776",
    }
