import os
from unittest.mock import MagicMock

from pytest import fixture

from bt_dualboot.application.sync import SyncService
from bt_dualboot.domain.enums import DeviceSource, PairingType
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

        sync_service.push(BluetoothDevice(mac=SAMPLE_PUSH_MAC1, adapter_mac="A4:6B:6C:9D:E2:FB"))
        # EXPECT no exceptions raised
        assert True

    def test_push_accept_single_mac(self, sync_service):
        sync_service.push(SAMPLE_PUSH_MAC1)
        self.assert_effect(sync_service)

    def test_push_accept_list_of_macs(self, sync_service):
        sync_service.push([SAMPLE_PUSH_MAC1])
        self.assert_effect(sync_service)

    def test_push_accept_single_bt_instance(self, sync_service):
        sync_service.push(BluetoothDevice(mac=SAMPLE_PUSH_MAC1, adapter_mac="A4:6B:6C:9D:E2:FB"))
        self.assert_effect(sync_service)

    def test_push_accept_list_of_bt_instances(self, sync_service):
        sync_service.push([BluetoothDevice(mac=SAMPLE_PUSH_MAC1, adapter_mac="A4:6B:6C:9D:E2:FB")])
        self.assert_effect(sync_service)

    def test_push_updates_multiple_devices(self, sync_service):
        sync_service.push([SAMPLE_PUSH_MAC1, SAMPLE_PUSH_MAC2])
        assert sync_service.devices_needs_sync() == []


class TestSyncService__DuckTyping:
    """Tests for _index_devices() duck-typing of read_all() and devices_unsyncable()."""

    @staticmethod
    def _mock_reader_with_read_all(syncable: list[BluetoothDevice], unsyncable: list[BluetoothDevice]) -> MagicMock:
        reader = MagicMock(spec=["read", "read_all"])
        reader.read.return_value = syncable
        reader.read_all.return_value = (syncable, unsyncable)
        return reader

    @staticmethod
    def _mock_reader_read_only(devices: list[BluetoothDevice]) -> MagicMock:
        reader = MagicMock(spec=["read"])
        reader.read.return_value = devices
        return reader

    def test_index_devices_calls_read_all_when_available(self):
        syncable = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            )
        ]
        unsyncable = [BluetoothDevice(mac="FF:EE:DD:CC:BB:AA", adapter_mac="11:11:11:11:11:11", name="NoKey Device")]
        linux_reader = self._mock_reader_with_read_all(syncable, unsyncable)
        win_reader = self._mock_reader_read_only([])
        writer = MagicMock()

        service = SyncService(linux_reader, win_reader, writer)
        service._index_devices()

        linux_reader.read_all.assert_called_once()
        assert service._unsyncable_devices == unsyncable

    def test_devices_unsyncable_returns_cached_list(self):
        syncable = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            )
        ]
        unsyncable = [BluetoothDevice(mac="FF:EE:DD:CC:BB:AA", adapter_mac="11:11:11:11:11:11")]
        linux_reader = self._mock_reader_with_read_all(syncable, unsyncable)
        win_reader = self._mock_reader_read_only([])
        writer = MagicMock()

        service = SyncService(linux_reader, win_reader, writer)
        result = service.devices_unsyncable()

        assert result == unsyncable

    def test_devices_unsyncable_empty_when_no_read_all(self):
        syncable = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            )
        ]
        linux_reader = self._mock_reader_read_only(syncable)
        win_reader = self._mock_reader_read_only([])
        writer = MagicMock()

        service = SyncService(linux_reader, win_reader, writer)
        result = service.devices_unsyncable()

        assert result == []

    def test_index_devices_falls_back_to_read_on_value_error(self):
        syncable = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            )
        ]
        linux_reader = MagicMock(spec=["read", "read_all"])
        linux_reader.read_all.side_effect = ValueError("not a tuple")
        linux_reader.read.return_value = syncable
        win_reader = self._mock_reader_read_only([])
        writer = MagicMock()

        service = SyncService(linux_reader, win_reader, writer)
        service._index_devices()

        linux_reader.read.assert_called_once()
        assert service._unsyncable_devices is None

    def test_flush_cache_clears_unsyncable(self):
        syncable = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            )
        ]
        unsyncable = [BluetoothDevice(mac="FF:EE:DD:CC:BB:AA", adapter_mac="11:11:11:11:11:11")]
        linux_reader = self._mock_reader_with_read_all(syncable, unsyncable)
        win_reader = self._mock_reader_read_only([])
        writer = MagicMock()

        service = SyncService(linux_reader, win_reader, writer)
        assert service.devices_unsyncable() == unsyncable

        service.flush_cache()
        # _unsyncable_devices is cleared, but devices_unsyncable() re-indexes
        # Verify the internal state is cleared
        assert service._unsyncable_devices is None

    """Verify push() merges pairing_data (Issue #33): Linux overrides, Windows-only fields preserved."""

    @staticmethod
    def _mock_reader(devices: list[BluetoothDevice]) -> MagicMock:
        reader = MagicMock()
        reader.read.return_value = devices
        return reader

    def _make_service(self, linux_devs, win_devs):
        writer = MagicMock()
        service = SyncService(self._mock_reader(linux_devs), self._mock_reader(win_devs), writer)
        service._index_devices()
        return service, writer

    def test_push_merges_pairing_data_preserves_windows_fields(self):
        linux_device = BluetoothDevice(
            mac="AA:BB:CC:DD:EE:FF",
            source=DeviceSource.LINUX,
            adapter_mac="A4:6B:6C:9D:E2:FB",
            pairing_key="AABBCCDD",
            pairing_type=PairingType.LONG_TERM_KEY,
            pairing_data={"Key": "AABBCCDD", "EncSize": "16", "EDiv": "100", "Rand": "200"},
        )
        windows_device = BluetoothDevice(
            mac="AA:BB:CC:DD:EE:FF",
            source=DeviceSource.WINDOWS,
            adapter_mac="A4:6B:6C:9D:E2:FB",
            pairing_key="EEFF0011",
            pairing_type=PairingType.LONG_TERM_KEY,
            pairing_data={
                "Key": "EEFF0011",
                "EncSize": "16",
                "EDiv": "50",
                "Rand": "60",
                "Address": "hex(b):ba,80,01,0c,6c,c0,00,00",
                "AddressType": "dword:00000000",
                "CentralIRKStatus": "dword:00000001",
                "AuthReq": "dword:00000020",
            },
        )

        service, writer = self._make_service([linux_device], [windows_device])
        service.push(["AA:BB:CC:DD:EE:FF"])

        written = writer.write_devices.call_args[0][0]
        assert len(written) == 1
        d = written[0]
        # Linux keys override
        assert d.pairing_data["Key"] == "AABBCCDD"
        assert d.pairing_data["EDiv"] == "100"
        # Windows-only fields preserved
        assert d.pairing_data["Address"] == "hex(b):ba,80,01,0c,6c,c0,00,00"
        assert d.pairing_data["AddressType"] == "dword:00000000"
        assert d.pairing_data["CentralIRKStatus"] == "dword:00000001"
        assert d.pairing_data["AuthReq"] == "dword:00000020"


class TestSyncService__MultiAdapter:
    """Tests for devices paired on multiple adapters (Issue #10)."""

    @staticmethod
    def _mock_reader(devices: list[BluetoothDevice]) -> MagicMock:
        reader = MagicMock()
        reader.read.return_value = devices
        return reader

    def _make_service(self, linux_devs, win_devs):
        writer = MagicMock()
        service = SyncService(self._mock_reader(linux_devs), self._mock_reader(win_devs), writer)
        service._index_devices()
        return service, writer

    def test_same_device_two_adapters_both_need_sync(self):
        linux_devs = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            ),
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="22:22:22:22:22:22",
                pairing_key="KEY2",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY2"},
            ),
        ]
        win_devs = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.WINDOWS,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="OLD1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "OLD1"},
            ),
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.WINDOWS,
                adapter_mac="22:22:22:22:22:22",
                pairing_key="OLD2",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "OLD2"},
            ),
        ]
        service, _writer = self._make_service(linux_devs, win_devs)
        assert len(service.devices_needs_sync()) == 2

    def test_same_device_one_synced_one_not(self):
        linux_devs = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            ),
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="22:22:22:22:22:22",
                pairing_key="KEY2",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY2"},
            ),
        ]
        win_devs = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.WINDOWS,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            ),
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.WINDOWS,
                adapter_mac="22:22:22:22:22:22",
                pairing_key="OLD2",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "OLD2"},
            ),
        ]
        service, _writer = self._make_service(linux_devs, win_devs)

        synced = service.devices_both_synced()
        assert len(synced) == 1
        assert synced[0].adapter_mac == "11:11:11:11:11:11"

        needs_sync = service.devices_needs_sync()
        assert len(needs_sync) == 1
        assert needs_sync[0].adapter_mac == "22:22:22:22:22:22"

    def test_push_syncs_all_adapter_pairs(self):
        linux_devs = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="KEY1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY1"},
            ),
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.LINUX,
                adapter_mac="22:22:22:22:22:22",
                pairing_key="KEY2",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "KEY2"},
            ),
        ]
        win_devs = [
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.WINDOWS,
                adapter_mac="11:11:11:11:11:11",
                pairing_key="OLD1",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "OLD1"},
            ),
            BluetoothDevice(
                mac="AA:BB:CC:DD:EE:FF",
                source=DeviceSource.WINDOWS,
                adapter_mac="22:22:22:22:22:22",
                pairing_key="OLD2",
                pairing_type=PairingType.LINK_KEY,
                pairing_data={"Key": "OLD2"},
            ),
        ]
        writer = MagicMock()
        service = SyncService(self._mock_reader(linux_devs), self._mock_reader(win_devs), writer)
        service._index_devices()
        service.push(["AA:BB:CC:DD:EE:FF"])

        written = writer.write_devices.call_args[0][0]
        assert len(written) == 2
        assert {d.adapter_mac for d in written} == {"11:11:11:11:11:11", "22:22:22:22:22:22"}
