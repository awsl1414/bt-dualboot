import os

from bt_dualboot.domain.enums import DeviceSource
from bt_dualboot.infrastructure.linux.reader import LinuxDeviceReader

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_samples")
SMPL_BT_SAMPLE_01 = os.path.join(SAMPLES_DIR, "bt_sample_01")


class TestLinuxDeviceReader:
    def test_read_returns_devices(self):
        reader = LinuxDeviceReader(bt_dir=SMPL_BT_SAMPLE_01)
        devices = reader.read()

        expected_macs = [
            "44:16:22:E6:73:15",
            "A4:BF:C6:D0:E5:FF",
            "AA:BB:CC:DD:EE:FF",
            "B6:C2:D3:E5:F2:0D",
            "C2:9E:1D:E2:3D:A5",
            "D1:8A:4E:71:5D:C1",
            "A4:80:1D:C5:4F:7E",
            "B8:94:A5:FD:F1:0A",
            "C4:72:B3:6F:82:42",
        ]
        actual_macs = [device.mac for device in devices]
        assert sorted(actual_macs) == sorted(expected_macs)

    def test_read_source_is_linux(self):
        reader = LinuxDeviceReader(bt_dir=SMPL_BT_SAMPLE_01)
        for device in reader.read():
            assert device.source == DeviceSource.LINUX

    def test_device_paths_finds_info_and_settings(self):
        reader = LinuxDeviceReader(bt_dir=SMPL_BT_SAMPLE_01)
        paths = reader._device_paths()
        assert len(paths) > 0

        info_paths = [p for p in paths if p.endswith("info")]
        settings_paths = [p for p in paths if p.endswith("settings")]
        assert len(info_paths) > 0
        assert len(settings_paths) > 0

    def test_read_all_separates_syncable_and_unsyncable(self):
        reader = LinuxDeviceReader(bt_dir=SMPL_BT_SAMPLE_01)
        syncable, unsyncable = reader.read_all()

        # Unsyncable device: 22:94:90:56:EE:38 has no LinkKey/LongTermKey
        unsyncable_macs = [d.mac for d in unsyncable]
        assert "22:94:90:56:EE:38" in unsyncable_macs

        # Syncable devices should NOT include the unsyncable one
        syncable_macs = [d.mac for d in syncable]
        assert "22:94:90:56:EE:38" not in syncable_macs

        # Unsyncable device should have name parsed from info file
        device = [d for d in unsyncable if d.mac == "22:94:90:56:EE:38"][0]
        assert device.name == "Some Device Without Key"
