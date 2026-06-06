from bt_dualboot.domain.enums import DeviceSource, PairingType
from bt_dualboot.infrastructure.registry.hive import WindowsRegistry
from bt_dualboot.infrastructure.windows.convert import mac_to_reg_key
from bt_dualboot.infrastructure.windows.parser import extract_adapter_mac
from bt_dualboot.infrastructure.windows.reader import WindowsDeviceReader

wp = WindowsRegistry.with_prefix

"""
@see tests/conftest.py for test set explanation
"""


def test_extract_adapter_mac():
    key = r"ControlSet001\Services\BTHPORT\Parameters\Keys\d46d6d97629b"
    assert extract_adapter_mac(key) == "D4:6D:6D:97:62:9B"


def test_get_devices(windows_registry, import_devices, test_scheme):
    reader = WindowsDeviceReader(windows_registry)
    devices = reader.read()

    for device in devices:
        assert device.mac in list(test_scheme[device.adapter_mac].keys())
        assert device.pairing_key == test_scheme[device.adapter_mac][device.mac]


def test_get_devices__source(windows_registry, import_devices):
    reader = WindowsDeviceReader(windows_registry)
    for device in reader.read():
        assert device.source == DeviceSource.WINDOWS


def test_get_devices__long_term_key(windows_registry):
    adapter_mac = "A4:6B:6C:9D:E2:FB"
    device_mac = "AA:BB:CC:DD:EE:FF"
    reg_section = wp(
        r"ControlSet001\Services\BTHPORT\Parameters\Keys"
        + "\\"
        + mac_to_reg_key(adapter_mac)
        + "\\"
        + mac_to_reg_key(device_mac)
    )
    windows_registry.import_dict(
        {
            reg_section: {
                '"LTK"': "hex:ff,ee,dd,cc,bb,aa,99,88,77,66,55,44,33,22,11,00",
                '"KeyLength"': "dword:00000010",
                '"EDIV"': "dword:00001234",
                '"ERand"': "hex(b):08,07,06,05,04,03,02,01",
                '"IRK"': "hex:00,11,22,33,44,55,66,77,88,99,aa,bb,cc,dd,ee,ff",
            }
        },
        safe=False,
    )

    reader = WindowsDeviceReader(windows_registry)
    devices = reader.read()
    device = [device for device in devices if device.mac == device_mac][0]

    assert device.adapter_mac == adapter_mac
    assert device.pairing_key == "FFEEDDCCBBAA99887766554433221100"
    assert device.pairing_type == PairingType.LONG_TERM_KEY
    assert device.pairing_data == {
        "Key": "FFEEDDCCBBAA99887766554433221100",
        "EncSize": "16",
        "EDiv": "4660",
        "Rand": "72623859790382856",
        "IRK": "00112233445566778899AABBCCDDEEFF",
    }


def test_get_devices__long_term_key_with_windows_only_fields(windows_registry):
    adapter_mac = "A4:6B:6C:9D:E2:FB"
    device_mac = "AA:BB:CC:DD:EE:FF"
    reg_section = wp(
        r"ControlSet001\Services\BTHPORT\Parameters\Keys"
        + "\\"
        + mac_to_reg_key(adapter_mac)
        + "\\"
        + mac_to_reg_key(device_mac)
    )
    windows_registry.import_dict(
        {
            reg_section: {
                '"LTK"': "hex:ff,ee,dd,cc,bb,aa,99,88,77,66,55,44,33,22,11,00",
                '"KeyLength"': "dword:00000010",
                '"EDIV"': "dword:00001234",
                '"ERand"': "hex(b):08,07,06,05,04,03,02,01",
                '"IRK"': "hex:00,11,22,33,44,55,66,77,88,99,aa,bb,cc,dd,ee,ff",
                '"Address"': "hex(b):ba,80,01,0c,6c,c0,00,00",
                '"AddressType"': "dword:00000000",
                '"CEntralIRKStatus"': "dword:00000001",
                '"AuthReq"': "dword:00000020",
            }
        },
        safe=False,
    )

    reader = WindowsDeviceReader(windows_registry)
    devices = reader.read()
    device = [d for d in devices if d.mac == device_mac][0]

    assert device.pairing_data["Address"] == "hex(b):ba,80,01,0c,6c,c0,00,00"
    assert device.pairing_data["AddressType"] == "dword:00000000"
    assert device.pairing_data["CentralIRKStatus"] == "dword:00000001"
    assert device.pairing_data["AuthReq"] == "dword:00000020"
