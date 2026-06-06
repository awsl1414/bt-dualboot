import os

from .registry.hive import WINDOWS10_REGISTRY_PATH
from .registry.resolve import resolve_path_ci

PROC_MOUNTS = "/proc/mounts"


def _mounts_to_try() -> list[str]:
    mounts = []
    with open(PROC_MOUNTS) as f:
        for line in f:
            if line.find("/dev") == 0 and line.find("/dev/loop") != 0:
                mount_point = line.split(" ")[1]
                mounts.append(mount_point)
    return mounts


def locate_windows_mount_points() -> list[str]:
    win_mount_points = []
    for mount_point in _mounts_to_try():
        resolved = resolve_path_ci(mount_point, WINDOWS10_REGISTRY_PATH)
        if os.path.isfile(resolved):
            win_mount_points.append(mount_point)
    return win_mount_points
