from dataclasses import dataclass, field

from .enums import DeviceSource, PairingType


@dataclass(slots=True, frozen=True, kw_only=True)
class BluetoothDevice:
    mac: str
    adapter_mac: str
    name: str | None = None
    pairing_key: str | None = None
    klass: str | None = None
    source: DeviceSource | None = None
    pairing_type: PairingType | None = None
    pairing_data: dict[str, str] = field(default_factory=dict)

    def is_pairing_type_long_term_key(self) -> bool:
        return self.pairing_type == PairingType.LONG_TERM_KEY

    def pairing_fingerprint(self) -> tuple[PairingType | None, tuple[tuple[str, str], ...]]:
        """Compare pairing data between two devices (replaces simple pairing_key comparison)"""
        return (
            self.pairing_type,
            tuple(sorted((k, str(v)) for k, v in self.pairing_data.items())),
        )
