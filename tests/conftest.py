import os
import shutil
from pathlib import Path

from pytest import fixture

from bt_dualboot.infrastructure.registry.hive import WindowsRegistry
from bt_dualboot.infrastructure.windows.convert import hex_string_to_reg_value, mac_to_reg_key

# --- windows_registry fixtures ---

wp = WindowsRegistry.with_prefix


@fixture
def windows_registry_samples_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "infrastructure", "registry", "data_samples")


@fixture
def sample_reg_file_path(windows_registry_samples_dir: str) -> str:
    """Windows/System32/config/SYSTEM snapshot from fresh-installed Windows 10"""
    return os.path.join(windows_registry_samples_dir, "SYSTEM_BLANK")


@fixture
def registry_file_path(sample_reg_file_path: str, tmp_path: Path):  # type: ignore[misc]
    """Making working copy of SYSTEM Hive file"""
    test_reg = str(tmp_path / "SYSTEM")
    shutil.copy(sample_reg_file_path, test_reg)
    os.chmod(test_reg, 0o600)
    yield test_reg
    os.unlink(test_reg)


@fixture
def windows_registry(registry_file_path: str) -> WindowsRegistry:
    return WindowsRegistry(registry_file_path)


# --- bt_linux fixtures ---


@fixture
def bt_linux_samples_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "infrastructure", "linux", "data_samples")


@fixture
def bt_linux_sample_01(bt_linux_samples_dir: str) -> str:
    return os.path.join(bt_linux_samples_dir, "bt_sample_01")


# --- bt_windows fixtures & constants ---

# valid for --sync*
MAC_NEED_SYNC_1: str = "B8:94:A5:FD:F1:0A"
MAC_NEED_SYNC_2: str = "C2:9E:1D:E2:3D:A5"

# not valid for --sync*
MAC_NO_WIN_PAIR_2: str = "D1:8A:4E:71:5D:C1"
UNKNOWN_MAC_1: str = "F2:9E:1D:E2:3D:A5"
UNKNOWN_MAC_2: str = "E8:94:A5:FD:F1:0A"


@fixture
def test_scheme() -> dict[str, dict[str, str]]:
    return {
        # adapter MAC
        "A4:6B:6C:9D:E2:FB": {
            # device MAC:        pairing_key                            NOTE
            # -----------        -----------                            ----
            "A4:BF:C6:D0:E5:FF": "A43C6BD9E1592C1FFA0DE17F3DB6F38B",  # same
            "B6:C2:D3:E5:F2:0D": "A515CBE4E8F2E236FF999C0A53369EF6",  # same
            "MasterIRK": "35353535353535353535353535353535",  # non-MAC value
            "C2:9E:1D:E2:3D:A5": "12121212121212121212121212121212",  # differ
            # absent 'D1:8A:4E:71:5D:C1'
            "E9:1D:FE:2A:C3:C8": "34343434343434343434343434343434",  # not paired in linux
        },
        "B4:6B:6C:9D:E2:FB": {
            "A4:80:1D:C5:4F:7E": "A12B5D441EC1A9D517794FC2B4889202",  # same
            "B8:94:A5:FD:F1:0A": "71717171717171717171717171717171",  # differ
            # absent 'C4:72:B3:6F:82:42'
        },
    }


@fixture
def import_devices(windows_registry: WindowsRegistry, test_scheme: dict[str, dict[str, str]]) -> None:
    for_import: dict[str, dict[str, str]] = {}

    for adapter_mac, devices in test_scheme.items():
        reg_section = wp(r"ControlSet001\Services\BTHPORT\Parameters\Keys" + "\\" + mac_to_reg_key(adapter_mac))
        for_import[reg_section] = {}

        for device_mac, pairing_key in devices.items():
            device_reg_key = mac_to_reg_key(device_mac) if device_mac != "MasterIRK" else device_mac

            for_import[reg_section][f'"{device_reg_key}"'] = hex_string_to_reg_value(pairing_key)

    windows_registry.import_dict(for_import, safe=False)
