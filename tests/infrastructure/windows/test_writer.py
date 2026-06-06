from bt_dualboot.domain.enums import PairingType
from bt_dualboot.domain.models import BluetoothDevice
from bt_dualboot.infrastructure.windows.writer import WindowsDeviceWriter


class TestBuildImportDict:
    def _make_writer(self, windows_registry) -> WindowsDeviceWriter:
        return WindowsDeviceWriter(windows_registry)

    def test_classic_device_flat_structure(self, windows_registry):
        writer = self._make_writer(windows_registry)
        device = BluetoothDevice(
            mac="D5:1F:FA:42:1C:4C",
            adapter_mac="A4:6B:6C:9D:E2:FB",
            pairing_key="A61B7F1BD9A35F3CF7E675EF2161A836",
            pairing_type=PairingType.LINK_KEY,
        )

        result = writer._build_import_dict([device])

        assert len(result) == 1
        section_key = r"ControlSet001\Services\BTHPORT\Parameters\Keys\a46b6c9de2fb"
        assert section_key in result
        assert '"d51ffa421c4c"' in result[section_key]
        assert result[section_key]['"d51ffa421c4c"'] == "hex:a6,1b,7f,1b,d9,a3,5f,3c,f7,e6,75,ef,21,61,a8,36"

    def test_ltk_device_nested_structure(self, windows_registry):
        writer = self._make_writer(windows_registry)
        device = BluetoothDevice(
            mac="D5:1F:FA:42:1C:4C",
            adapter_mac="A4:6B:6C:9D:E2:FB",
            pairing_key="FFEEDDCCBBAA99887766554433221100",
            pairing_type=PairingType.LONG_TERM_KEY,
            pairing_data={
                "Key": "FFEEDDCCBBAA99887766554433221100",
                "EncSize": "16",
                "EDiv": "4660",
                "Rand": "72623859790382856",
                "IRK": "00112233445566778899AABBCCDDEEFF",
            },
        )

        result = writer._build_import_dict([device])

        assert len(result) == 1
        section_key = r"ControlSet001\Services\BTHPORT\Parameters\Keys\a46b6c9de2fb\d51ffa421c4c"
        assert section_key in result
        section = result[section_key]
        assert '"LTK"' in section
        assert '"KeyLength"' in section
        assert '"EDIV"' in section
        assert '"ERand"' in section
        assert '"IRK"' in section

    def test_write_devices_updates_existing_key(self, windows_registry, import_devices):
        """Write a new pairing key for a device already in the registry (safe=True)."""
        writer = self._make_writer(windows_registry)
        device = BluetoothDevice(
            mac="A4:BF:C6:D0:E5:FF",
            adapter_mac="A4:6B:6C:9D:E2:FB",
            pairing_key="AAAABBBBCCCCDDDDEEEEFFFF00001111",
            pairing_type=PairingType.LINK_KEY,
            pairing_data={"Key": "AAAABBBBCCCCDDDDEEEEFFFF00001111"},
        )

        writer.write_devices([device])
        # Should not raise — same-size update via safe=True
