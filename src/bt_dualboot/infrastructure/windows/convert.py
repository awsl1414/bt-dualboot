import re

# MAC address = 6 bytes = 12 hex characters (no separators)
_MAC_HEX_LENGTH = 12

# Registry value format widths
_DWORD_HEX_WIDTH = 8  # 32-bit = 4 bytes = 8 hex chars
_QWORD_HEX_WIDTH = 16  # 64-bit = 8 bytes = 16 hex chars


def hex_string_to_pairs(hex_string: str) -> list[str]:
    """Convert hex string to pairs array"""
    buf = hex_string
    buf_len = len(buf)

    if buf_len % 2 != 0:
        raise RuntimeError(f"wrong hex string={hex_string}")

    pairs_count = buf_len // 2

    pairs = []
    for i in range(pairs_count):
        start = i * 2
        end = start + 2
        pairs.append(buf[start:end])

    return pairs


def is_mac_reg_key(value: str) -> bool:
    """Check is value is valid MAC reg key"""
    return re.match(f"^[a-f0-9]{{{_MAC_HEX_LENGTH}}}$", _unquote(value)) is not None


def mac_from_reg_key(mac_key: str) -> str:
    """Convert device MAC from Windows registry key format to regular"""
    return ":".join(hex_string_to_pairs(_unquote(mac_key).upper()))


def mac_to_reg_key(mac: str) -> str:
    """Convert device MAC to Windows registry key format"""
    return "".join(mac.split(":")).lower()


def hex_string_from_reg(hex_string_reg: str) -> str:
    """Convert hex string from Windows registry format"""
    _, value = hex_string_reg.split(":")
    return "".join(value.split(",")).upper()


def hex_string_to_reg_value(hex_string: str) -> str:
    """Convert hex string to Windows registry value"""
    value = ",".join(hex_string_to_pairs(hex_string.lower()))
    return f"hex:{value}"


def _reg_value_type_and_value(reg_value: str) -> tuple[str, str]:
    """Split registry value into type and value parts"""
    value_type, value = reg_value.split(":", 1)
    return value_type.lower(), value


def _bytes_from_reg_value(reg_value: str) -> list[str]:
    """Extract byte list from registry value, supports hex/hex(b)/dword"""
    value_type, value = _reg_value_type_and_value(reg_value)

    if value_type == "dword":
        return hex_string_to_pairs(value.upper())

    if value_type in ["hex", "hex(b)"]:
        return [pair.strip().upper() for pair in value.split(",") if pair.strip() != ""]

    raise RuntimeError(f"unsupported registry value={reg_value}")


def int_from_le_reg_value(reg_value: str) -> int:
    """Convert little-endian Windows registry value to int

    Supports REG_BINARY/REG_QWORD byte lists and REG_DWORD values.
    """
    value_type, value = _reg_value_type_and_value(reg_value)

    if value_type == "dword":
        return int(value, 16)

    pairs = _bytes_from_reg_value(reg_value)
    return int("".join(pairs[::-1]), 16)


def int_to_dword_reg_value(value: int | str) -> str:
    """Convert int to Windows registry dword value"""
    return f"dword:{int(value):0{_DWORD_HEX_WIDTH}x}"


def int_to_qword_reg_value(value: int | str) -> str:
    """Convert int to Windows registry qword value (little-endian hex(b))"""
    pairs = hex_string_to_pairs(f"{int(value):0{_QWORD_HEX_WIDTH}x}")
    return f"hex(b):{','.join(pairs[::-1])}"


def _unquote(value: str) -> str:
    """unquote value is quoted"""
    if value[0] == '"' and value[-1] == '"':
        return value[1:-1]

    return value
