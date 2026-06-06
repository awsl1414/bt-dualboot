import os
import shutil
import sys


def action_requires_root(opts) -> bool:
    """Check if the requested CLI action requires root privileges.

    Args:
        opts: Parsed argparse namespace.

    Returns:
        True if the action needs root access to /var/lib/bluetooth or Windows registry.
    """
    return any([opts.list, opts.sync is not None, opts.sync_all])


def elevate_via_sudo() -> None:
    """Re-execute the current process under sudo if not already root.

    Preserves the DEBUG environment variable across the sudo boundary.
    Calls os.execvp which does not return on success.

    Raises:
        SystemExit: If not running as root and sudo is not available.
    """
    if os.geteuid() == 0:
        return

    sudo_path = shutil.which("sudo")
    if sudo_path is None:
        raise SystemExit(
            "ERROR: This action requires root privileges.\nPlease run with sudo or install the sudo package."
        )

    cmd = _build_reexec_argv()
    preserve_env = []
    if os.environ.get("DEBUG") == "1":
        preserve_env = ["--preserve-env=DEBUG"]

    print("Elevating privileges via sudo...", file=sys.stderr)
    os.execvp(sudo_path, [sudo_path, *preserve_env, *cmd])


def _build_reexec_argv() -> list[str]:
    """Build the argv for re-executing the current process.

    Prefers the entry script if it exists and is executable,
    otherwise falls back to ``python -m bt_dualboot``.
    """
    entry_script = _find_entry_script()
    if entry_script is not None:
        return [entry_script, *sys.argv[1:]]

    return [sys.executable, "-m", "bt_dualboot", *sys.argv[1:]]


def _find_entry_script() -> str | None:
    """Find the bt-dualboot entry script on PATH."""
    from bt_dualboot import APP_NAME

    path = shutil.which(APP_NAME)
    if path is not None and os.access(path, os.X_OK):
        return path

    return None
