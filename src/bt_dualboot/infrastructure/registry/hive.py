import os
import shutil
import subprocess
from configparser import ConfigParser
from datetime import datetime
from tempfile import TemporaryDirectory

from bt_dualboot._debug import is_debug

from .resolve import resolve_path_ci

WINDOWS10_REGISTRY_PATH: str = os.path.join("Windows", "System32", "config", "SYSTEM")

# reged (from chntpw) returns 2 on successful import, not the conventional 0.
_REGED_SUCCESS_EXIT_CODE = 2


def _run_quiet(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Run subprocess, suppressing output unless debug mode."""
    if is_debug():
        return subprocess.run(cmd)
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class WindowsRegistry:
    """Represents Windows registry"""

    def __init__(
        self,
        registry_file_path: str | None = None,
        windows_path: str | None = None,
        relative_registry_path: str = WINDOWS10_REGISTRY_PATH,
    ) -> None:
        self.registry_file_path = registry_file_path
        self.windows_path = windows_path
        self.relative_registry_path = relative_registry_path

    @classmethod
    def exchange_prefix(cls) -> str:
        """Prefix for import/export using chntpw/reged"""
        return "PYTHONCHNTPWEXCHANGE"

    @classmethod
    def with_prefix(cls, key: str) -> str:
        return cls.exchange_prefix() + "\\" + key

    @classmethod
    def reg_file_signature(cls) -> str:
        return "Windows Registry Editor Version 5.00"

    def _registry_file(self) -> str:
        if self.registry_file_path is not None:
            return self.registry_file_path

        assert self.windows_path is not None
        return resolve_path_ci(self.windows_path, self.relative_registry_path)

    def export(self, reg_key: str) -> str:
        """Exports given registry key as text"""
        with TemporaryDirectory() as temp_dir_name:
            exported_reg_filename = os.path.join(temp_dir_name, "exported.reg")
            export_cmd = [
                "reged",
                "-x",
                self._registry_file(),
                self.exchange_prefix(),
                reg_key,
                exported_reg_filename,
            ]
            _run_quiet(export_cmd)

            with open(exported_reg_filename) as f:
                # skip first line "Windows Registry Editor Version 5.00" for ConfigParser compability
                exported_text = "".join(f.readlines()[1:])

        if is_debug():
            print("Exported from Windows registry:")
            print(exported_text)

        return exported_text

    def backup(self, backup_path: str, dry_run: bool) -> tuple[str, str]:
        """Backups Hive file to given path

        Returns:
            (str, str): backup_file_path, target_file_path
        """
        target_file_path = self._registry_file()
        timestamp = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
        reg_filename = target_file_path.split(os.sep)[-1]
        backup_filename = f"{reg_filename}-{timestamp}"
        backup_file_path = os.path.join(backup_path, backup_filename)

        if dry_run is not True:
            os.makedirs(backup_path, exist_ok=True)
            shutil.copy(target_file_path, backup_file_path)

        return backup_file_path, target_file_path

    def export_as_config(self, reg_key: str) -> ConfigParser:
        """Exports given registry key as ConfigParser instance"""
        reg_data = ConfigParser()
        reg_data.read_string(self.export(reg_key))
        return reg_data

    def import_dict(self, data_dict: dict[str, dict[str, str]], safe: bool = True, auto_prefix: bool = True) -> None:
        """Imports given dict into Windows registry"""
        registry_file = self._registry_file()
        if not os.access(registry_file, os.W_OK):
            raise PermissionError(
                f"Windows registry file is not writable: {registry_file}\n"
                "Ensure the Windows partition is mounted with write access (e.g. remount with -o rw)."
            )
        with TemporaryDirectory() as temp_dir_name:
            tmp_filename = os.path.join(temp_dir_name, "for_import.reg")

            with open(tmp_filename, "w") as f:
                print(self.reg_file_signature(), file=f)

                for inp_section_key in data_dict:
                    reg_section_key = inp_section_key
                    if auto_prefix and reg_section_key[0] != "\\" and reg_section_key.find(self.exchange_prefix()) < 0:
                        reg_section_key = self.exchange_prefix() + "\\" + reg_section_key

                    print(file=f)
                    print(f"[{reg_section_key}]", file=f)

                    section_data = data_dict[inp_section_key]
                    for key in section_data:
                        print(f"{key}={section_data[key]}", file=f)

            safe_args: list[str] = []
            if safe is True:
                safe_args = ["-N", "-E"]

            import_cmd = [
                "reged",
                *safe_args,
                "-I",
                "-C",
                self._registry_file(),
                self.exchange_prefix(),
                tmp_filename,
            ]
            res = _run_quiet(import_cmd)

            if is_debug():
                print("Importing into Windows registry...")
                with open(tmp_filename) as f:
                    print(f.read())

            os.unlink(tmp_filename)

            if res.returncode != _REGED_SUCCESS_EXIT_CODE:
                raise RuntimeError(
                    "Data couldn't be saved! See reged output for details using DEBUG=1. Try .import_dict(safe=False)"
                )
