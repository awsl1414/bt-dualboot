"""Shared BLE key mappings for reader and writer.

Single source of truth for optional and Windows-only BLE registry fields.
Reader uses the lowercase keys for lookup; writer uses the quoted keys for output.
"""

# BLE optional pairing fields (data_key → registry key name)
BLE_OPTIONAL_KEYS: tuple[str, ...] = ("IRK", "CSRK", "CSRKInbound")

# Windows-only registry fields preserved for round-trip (Issue #33)
WINDOWS_ONLY_KEYS: tuple[str, ...] = ("Address", "AddressType", "AuthReq", "CentralIRKStatus")


def reader_optional_key_map() -> dict[str, str]:
    """Map data_key → lowercase registry key (for reader lookup in lowercased section)."""
    return {key: key.lower() for key in BLE_OPTIONAL_KEYS}


def reader_windows_only_key_map() -> dict[str, str]:
    """Map data_key → lowercase registry key (for reader lookup in lowercased section)."""
    return {key: key.lower() for key in WINDOWS_ONLY_KEYS}


def writer_optional_key_map() -> dict[str, str]:
    """Map data_key → quoted registry key (for writer output to .reg file)."""
    return {key: f'"{key}"' for key in BLE_OPTIONAL_KEYS}


def writer_windows_only_key_map() -> dict[str, str]:
    """Map data_key → quoted registry key (for writer output to .reg file)."""
    return {key: f'"{key}"' for key in WINDOWS_ONLY_KEYS}
