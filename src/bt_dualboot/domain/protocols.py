from typing import Protocol

from .models import BluetoothDevice


class DeviceReader(Protocol):
    def read(self) -> list[BluetoothDevice]: ...


class DeviceWriter(Protocol):
    def write_devices(self, devices: list[BluetoothDevice]) -> None: ...
