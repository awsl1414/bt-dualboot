import re
from unittest.mock import patch

import pytest

from bt_dualboot import __version__
from bt_dualboot.cli.main import print_devices_list, require_univocal_windows_location
from bt_dualboot.domain.models import BluetoothDevice


def _print_with_common_args(*args, **kwrd):
    print_devices_list(
        "cap",
        "Caption",
        *args,
        annotation="The Annotation",
        message_not_found="not found",
        **kwrd
    )  # fmt: skip


_ADAPTER_A = "11:11:11:11:11:11"


def test_version():
    with open("pyproject.toml") as f:
        for line in f:
            res = re.match(r"^version = ['\"](\d+\.\d+\.\d+)['\"]\s*", line)

            if res is not None:
                pyproject_toml_version = res.groups()[0]
                assert __version__ == pyproject_toml_version, (
                    "version mismatch between pyproject.toml and bt_dualboot.__version__;"
                    " invoke dev/pre-release/update-version to fix"
                )
                return

    raise AssertionError("no version= found in pyproject.toml")


class Test__print_devices_list:
    def test_bot_two_devices(self, capsys):
        _print_with_common_args(
            [
                BluetoothDevice(mac="AA:BB:CC:11", adapter_mac=_ADAPTER_A, name="Device Name #1"),
                BluetoothDevice(mac="AA:BB:CC:22", adapter_mac=_ADAPTER_A, name="Device Name #2"),
            ],
            bot=True,
        )
        stdout, stderr = capsys.readouterr()
        assert stdout == "cap AA:BB:CC:11 Device Name #1\ncap AA:BB:CC:22 Device Name #2\n"

    def test_bot_none(self, capsys):
        _print_with_common_args([], bot=True)
        stdout, stderr = capsys.readouterr()
        assert stdout == "cap NONE\n"

    def test_two_devices(self, capsys, snapshot):
        _print_with_common_args(
            [
                BluetoothDevice(mac="AA:BB:CC:11", adapter_mac=_ADAPTER_A, name="Device Name #1"),
                BluetoothDevice(mac="AA:BB:CC:22", adapter_mac=_ADAPTER_A, name="Device Name #2"),
            ],
        )
        stdout, stderr = capsys.readouterr()
        assert stdout == snapshot

    def test_none(self, capsys, snapshot):
        _print_with_common_args([])
        stdout, stderr = capsys.readouterr()
        assert stdout == snapshot


class TestRequireUnivocalWindowsLocation:
    def test_user_selected_location_skips_check(self):
        require_univocal_windows_location("/mnt/windows")

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=[])
    def test_zero_locations_shows_mount_guidance(self, mock_mounts):
        with pytest.raises(SystemExit) as exc_info:
            require_univocal_windows_location(None)
        msg = str(exc_info.value)
        assert "No Windows locations found" in msg
        assert "lsblk -f" in msg
        assert "--win" in msg

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/a", "/mnt/b"])
    def test_multiple_locations_lists_paths(self, mock_mounts):
        with pytest.raises(SystemExit) as exc_info:
            require_univocal_windows_location(None)
        msg = str(exc_info.value)
        assert "Multiple Windows locations found" in msg
        assert "/mnt/a" in msg
        assert "/mnt/b" in msg
        assert "--win" in msg

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/win"])
    def test_single_location_does_not_raise(self, mock_mounts):
        require_univocal_windows_location(None)


class TestPrintDevicesList__MultiAdapter:
    def test_shows_adapter_when_multiple_adapters(self, capsys):
        print_devices_list(
            "cap",
            "Caption",
            [
                BluetoothDevice(mac="AA:BB:CC:11", name="Dev1", adapter_mac="11:11:11:11:11:11"),
                BluetoothDevice(mac="AA:BB:CC:22", name="Dev2", adapter_mac="22:22:22:22:22:22"),
            ],
        )
        stdout, _stderr = capsys.readouterr()
        assert "11:11:11:11:11:11" in stdout
        assert "22:22:22:22:22:22" in stdout

    def test_hides_adapter_when_single_adapter(self, capsys):
        print_devices_list(
            "cap",
            "Caption",
            [
                BluetoothDevice(mac="AA:BB:CC:11", name="Dev1", adapter_mac="11:11:11:11:11:11"),
                BluetoothDevice(mac="AA:BB:CC:22", name="Dev2", adapter_mac="11:11:11:11:11:11"),
            ],
        )
        stdout, _stderr = capsys.readouterr()
        assert "11:11:11:11:11:11" not in stdout

    def test_bot_shows_adapter_when_multiple_adapters(self, capsys):
        print_devices_list(
            "cap",
            "Caption",
            [
                BluetoothDevice(mac="AA:BB:CC:11", name="Dev1", adapter_mac="11:11:11:11:11:11"),
                BluetoothDevice(mac="AA:BB:CC:22", name="Dev2", adapter_mac="22:22:22:22:22:22"),
            ],
            bot=True,
        )
        stdout, _stderr = capsys.readouterr()
        assert "11:11:11:11:11:11" in stdout
        assert "22:22:22:22:22:22" in stdout
