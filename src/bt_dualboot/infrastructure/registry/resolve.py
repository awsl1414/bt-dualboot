import os


def resolve_path_ci(base: str, relative: str) -> str:
    """Resolve a relative path under base with case-insensitive fallback.

    On Linux, NTFS mounts may be case-sensitive. Windows paths like
    ``Windows/System32/config/SYSTEM`` might appear on disk as
    ``windows/system32/config/system``. This function walks each segment,
    preferring exact match but falling back to case-insensitive ``listdir``
    lookup.

    If any segment cannot be resolved, returns ``os.path.join(base, relative)``
    unchanged so that downstream error messages reference the requested path.

    Args:
        base: Absolute base directory (e.g. a mount point).
        relative: Relative path to resolve (e.g. ``Windows/System32/config/SYSTEM``).

    Returns:
        The resolved absolute path, or ``os.path.join(base, relative)`` if
        resolution fails.
    """
    target = os.path.join(base, relative)

    # Fast path: exact match exists
    if os.path.exists(target):
        return target

    # Walk each segment with case-insensitive fallback
    current = base
    segments = relative.replace("\\", "/").split("/")

    for segment in segments:
        exact = os.path.join(current, segment)
        if os.path.exists(exact):
            current = exact
            continue

        # Case-insensitive lookup
        if not os.path.isdir(current):
            return target

        try:
            entries = os.listdir(current)
        except OSError:
            return target

        lower_segment = segment.lower()
        match = None
        for entry in entries:
            if entry.lower() == lower_segment:
                match = entry
                break

        if match is None:
            return target

        current = os.path.join(current, match)

    return current
