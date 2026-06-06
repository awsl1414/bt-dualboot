import pytest

from bt_dualboot.domain.enums import DeviceSource, PairingType
from bt_dualboot.domain.models import BluetoothDevice


class TestBluetoothDevice:
    def test_construction_with_keyword_args(self):
        device = BluetoothDevice(mac="AA:BB:CC:DD:EE:FF", name="Test Device")
        assert device.mac == "AA:BB:CC:DD:EE:FF"
        assert device.name == "Test Device"

    def test_default_values(self):
        device = BluetoothDevice()
        assert device.mac is None
        assert device.name is None
        assert device.pairing_key is None
        assert device.adapter_mac is None
        assert device.klass is None
        assert device.source is None
        assert device.pairing_type is None
        assert device.pairing_data == {}

    def test_frozen_prevents_mutation(self):
        device = BluetoothDevice(mac="AA:BB")
        with pytest.raises(AttributeError):
            device.mac = "CC:DD"

    def test_kw_only_prevents_positional_args(self):
        with pytest.raises(TypeError):
            BluetoothDevice("AA:BB")  # type: ignore[misc]

    def test_source_enum_type(self):
        device = BluetoothDevice(source=DeviceSource.LINUX)
        assert device.source == DeviceSource.LINUX
        assert device.source == "Linux"

    def test_pairing_type_enum_type(self):
        device = BluetoothDevice(pairing_type=PairingType.LINK_KEY)
        assert device.pairing_type == PairingType.LINK_KEY
        assert device.pairing_type == "LinkKey"

    def test_pairing_data_default_factory(self):
        device1 = BluetoothDevice()
        device2 = BluetoothDevice()
        device1.pairing_data["Key"] = "AAA"
        assert device2.pairing_data == {}

    def test_is_pairing_type_long_term_key(self):
        device_ltk = BluetoothDevice(pairing_type=PairingType.LONG_TERM_KEY)
        device_lk = BluetoothDevice(pairing_type=PairingType.LINK_KEY)
        assert device_ltk.is_pairing_type_long_term_key()
        assert not device_lk.is_pairing_type_long_term_key()

    def test_pairing_fingerprint(self):
        device = BluetoothDevice(
            pairing_type=PairingType.LINK_KEY,
            pairing_data={"Key": "AABB"},
        )
        result = device.pairing_fingerprint()
        assert result[0] == PairingType.LINK_KEY
        assert result[1] == (("Key", "AABB"),)

    def test_pairing_fingerprint_sorted(self):
        device = BluetoothDevice(
            pairing_type=PairingType.LONG_TERM_KEY,
            pairing_data={"Key": "AABB", "EDiv": "0"},
        )
        result = device.pairing_fingerprint()
        assert result[1] == (("EDiv", "0"), ("Key", "AABB"))

    def test_klass_field(self):
        device = BluetoothDevice(klass="0x000540")
        assert device.klass == "0x000540"
