import os

from pytest import fixture

from bt_dualboot.application.sync import SyncService
from bt_dualboot.domain.models import BluetoothDevice
from bt_dualboot.infrastructure.linux.reader import LinuxDeviceReader
from bt_dualboot.infrastructure.windows.reader import WindowsDeviceReader
from bt_dualboot.infrastructure.windows.writer import WindowsDeviceWriter

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "infrastructure", "linux", "data_samples")
SMPL_BT_SAMPLE_01 = os.path.join(SAMPLES_DIR, "bt_sample_01")

SAMPLE_PUSH_MAC1 = "C2:9E:1D:E2:3D:A5"
SAMPLE_PUSH_MAC2 = "B8:94:A5:FD:F1:0A"


@fixture
def sync_service(import_devices, windows_registry):
    linux_reader = LinuxDeviceReader(bt_dir=SMPL_BT_SAMPLE_01)
    windows_reader = WindowsDeviceReader(windows_registry)
    writer = WindowsDeviceWriter(windows_registry)
    return SyncService(linux_reader, windows_reader, writer)


@fixture
def just_pushed(sync_service):
    sync_service.push([SAMPLE_PUSH_MAC1])
    sync_service.flush_cache()


class TestSyncService__Initial:
    def test_devices_both_synced(self, sync_service):
        expected_macs = ["A4:BF:C6:D0:E5:FF", "B6:C2:D3:E5:F2:0D", "A4:80:1D:C5:4F:7E"]

        devices = sync_service.devices_both_synced()
        devices_macs = [device.mac for device in devices]
        assert sorted(devices_macs) == sorted(expected_macs)

    def test_devices_needs_sync(self, sync_service):
        expected_macs = [
            "C2:9E:1D:E2:3D:A5",
            "B8:94:A5:FD:F1:0A",
        ]

        devices = sync_service.devices_needs_sync()
        devices_macs = [device.mac for device in devices]
        assert sorted(devices_macs) == sorted(expected_macs)

    def test_devices_absent_windows(self, sync_service):
        expected_macs = [
            "44:16:22:E6:73:15",
            "AA:BB:CC:DD:EE:FF",
            "D1:8A:4E:71:5D:C1",
            "C4:72:B3:6F:82:42",
        ]

        devices = sync_service.devices_absent_windows()
        devices_macs = [device.mac for device in devices]
        assert sorted(devices_macs) == sorted(expected_macs)


class TestSyncService__AfterSync:
    def test_devices_both_synced(self, sync_service, just_pushed):
        expected_macs = [
            "A4:BF:C6:D0:E5:FF",
            "B6:C2:D3:E5:F2:0D",
            "A4:80:1D:C5:4F:7E",
            "C2:9E:1D:E2:3D:A5",
        ]

        devices = sync_service.devices_both_synced()
        devices_macs = [device.mac for device in devices]
        assert sorted(devices_macs) == sorted(expected_macs)

    def test_devices_needs_sync(self, sync_service, just_pushed):
        expected_macs = [
            "B8:94:A5:FD:F1:0A",
        ]

        devices = sync_service.devices_needs_sync()
        devices_macs = [device.mac for device in devices]
        assert sorted(devices_macs) == sorted(expected_macs)

    def test_devices_absent_windows(self, sync_service, just_pushed):
        expected_macs = [
            "44:16:22:E6:73:15",
            "AA:BB:CC:DD:EE:FF",
            "D1:8A:4E:71:5D:C1",
            "C4:72:B3:6F:82:42",
        ]

        devices = sync_service.devices_absent_windows()
        devices_macs = [device.mac for device in devices]
        assert sorted(devices_macs) == sorted(expected_macs)


class TestSyncService__push:
    def assert_effect(self, sync_service):
        expected_macs = ["B8:94:A5:FD:F1:0A"]

        devices = sync_service.devices_needs_sync()
        devices_macs = [device.mac for device in devices]
        assert sorted(devices_macs) == sorted(expected_macs)

    def test_ensure_push_resets_cache(self, sync_service):
        # populate & corrupt cache
        sync_service.devices_needs_sync()
        sync_service._index_cache[SAMPLE_PUSH_MAC1].pop()

        sync_service.push(BluetoothDevice(mac=SAMPLE_PUSH_MAC1))
        # EXPECT no exceptions raised
        assert True

    def test_push_accept_single_mac(self, sync_service):
        sync_service.push(SAMPLE_PUSH_MAC1)
        self.assert_effect(sync_service)

    def test_push_accept_list_of_macs(self, sync_service):
        sync_service.push([SAMPLE_PUSH_MAC1])
        self.assert_effect(sync_service)

    def test_push_accept_single_bt_instance(self, sync_service):
        sync_service.push(BluetoothDevice(mac=SAMPLE_PUSH_MAC1))
        self.assert_effect(sync_service)

    def test_push_accept_list_of_bt_instances(self, sync_service):
        sync_service.push([BluetoothDevice(mac=SAMPLE_PUSH_MAC1)])
        self.assert_effect(sync_service)

    def test_push_updates_multiple_devices(self, sync_service):
        sync_service.push([SAMPLE_PUSH_MAC1, SAMPLE_PUSH_MAC2])
        assert sync_service.devices_needs_sync() == []
