import re
from unittest.mock import patch

import pytest

from bt_dualboot import __version__
from bt_dualboot.cli.main import (
    _argv_parser,
    _parse_selection,
    print_devices_list,
    resolve_windows_location,
)
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


class TestResolveWindowsLocation:
    def test_user_selected_location_returns_single(self):
        assert resolve_windows_location("/mnt/windows") == ["/mnt/windows"]

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=[])
    def test_zero_locations_shows_mount_guidance(self, mock_mounts):
        with pytest.raises(SystemExit) as exc_info:
            resolve_windows_location(None)
        msg = str(exc_info.value)
        assert "No Windows locations found" in msg
        assert "lsblk -f" in msg
        assert "-w" in msg

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/win"])
    def test_single_location_auto_selects(self, mock_mounts):
        assert resolve_windows_location(None) == ["/mnt/win"]

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/a", "/mnt/b"])
    @patch("bt_dualboot.cli.main.input", return_value="1")
    @patch("bt_dualboot.cli.main.sys")
    def test_multiple_locations_interactive_select_one(self, mock_sys, mock_input, mock_mounts):
        mock_sys.stdin.isatty.return_value = True
        assert resolve_windows_location(None) == ["/mnt/a"]

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/a", "/mnt/b"])
    @patch("bt_dualboot.cli.main.input", return_value="all")
    @patch("bt_dualboot.cli.main.sys")
    def test_multiple_locations_interactive_select_all(self, mock_sys, mock_input, mock_mounts):
        mock_sys.stdin.isatty.return_value = True
        assert resolve_windows_location(None) == ["/mnt/a", "/mnt/b"]

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/a", "/mnt/b", "/mnt/c"])
    @patch("bt_dualboot.cli.main.input", return_value="1,3")
    @patch("bt_dualboot.cli.main.sys")
    def test_multiple_locations_interactive_select_comma(self, mock_sys, mock_input, mock_mounts):
        mock_sys.stdin.isatty.return_value = True
        assert resolve_windows_location(None) == ["/mnt/a", "/mnt/c"]

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/a", "/mnt/b"])
    @patch("bt_dualboot.cli.main.sys")
    def test_multiple_locations_non_tty_raises(self, mock_sys, mock_mounts):
        mock_sys.stdin.isatty.return_value = False
        with pytest.raises(SystemExit) as exc_info:
            resolve_windows_location(None)
        msg = str(exc_info.value)
        assert "non-interactive" in msg
        assert "-w" in msg
        assert "/mnt/a" in msg
        assert "/mnt/b" in msg

    @patch("bt_dualboot.cli.main.locate_windows_mount_points", return_value=["/mnt/a", "/mnt/b"])
    def test_multiple_locations_bot_mode_raises(self, mock_mounts):
        with pytest.raises(SystemExit) as exc_info:
            resolve_windows_location(None, bot=True)
        msg = str(exc_info.value)
        assert "bot mode" in msg
        assert "/mnt/a" in msg
        assert "/mnt/b" in msg


class TestParseSelection:
    def test_single_number(self):
        assert _parse_selection("1", 3) == [0]

    def test_comma_separated(self):
        assert _parse_selection("1,3", 3) == [0, 2]

    def test_range(self):
        assert _parse_selection("1-3", 3) == [0, 1, 2]

    def test_mixed(self):
        assert _parse_selection("1,3-4", 4) == [0, 2, 3]

    def test_out_of_range_returns_none(self):
        assert _parse_selection("5", 3) is None

    def test_invalid_text_returns_none(self):
        assert _parse_selection("abc", 3) is None

    def test_empty_returns_none(self):
        assert _parse_selection("", 3) is None


class TestShortOptions:
    def test_sync_all_short(self):
        opts = _argv_parser().parse_args(["-a"])
        assert opts.sync_all is True

    def test_sync_short(self):
        opts = _argv_parser().parse_args(["-s", "AA:BB:CC:DD:EE:FF"])
        assert opts.sync == ["AA:BB:CC:DD:EE:FF"]

    def test_dry_run_short(self):
        opts = _argv_parser().parse_args(["-d"])
        assert opts.dry_run is True

    def test_win_short(self):
        opts = _argv_parser().parse_args(["-w", "/mnt/win"])
        assert opts.win == ["/mnt/win"]

    def test_combined_short_options(self):
        opts = _argv_parser().parse_args(["-a", "-d", "-w", "/mnt/win"])
        assert opts.sync_all is True
        assert opts.dry_run is True
        assert opts.win == ["/mnt/win"]


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
