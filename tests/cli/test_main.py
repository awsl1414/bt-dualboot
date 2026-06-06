import re

from bt_dualboot import __version__
from bt_dualboot.cli.main import print_devices_list
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
                BluetoothDevice(mac="AA:BB:CC:11", name="Device Name #1"),
                BluetoothDevice(mac="AA:BB:CC:22", name="Device Name #2"),
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
                BluetoothDevice(mac="AA:BB:CC:11", name="Device Name #1"),
                BluetoothDevice(mac="AA:BB:CC:22", name="Device Name #2"),
            ],
        )
        stdout, stderr = capsys.readouterr()
        assert stdout == snapshot

    def test_none(self, capsys, snapshot):
        _print_with_common_args([])
        stdout, stderr = capsys.readouterr()
        assert stdout == snapshot
