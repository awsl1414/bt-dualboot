from enum import StrEnum


class PairingType(StrEnum):
    LINK_KEY = "LinkKey"
    LONG_TERM_KEY = "LongTermKey"


class DeviceSource(StrEnum):
    LINUX = "Linux"
    WINDOWS = "Windows"
