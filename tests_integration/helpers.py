import os
import subprocess
import sys
from collections.abc import Generator
from contextlib import contextmanager
from operator import itemgetter
from pathlib import Path
from typing import Any

from pytest import fixture

from bt_dualboot import APP_NAME


@fixture(scope="session")
def debug_shell(request: Any) -> Any:
    """Spawn debug /bin/bash in middle of pytest session.
    Useful to debug Docker context between setup and teardown states.
    """

    @contextmanager
    def runner(
        shell: str = "/bin/bash", cmd_opts: list[str] | None = None, *subprocess_args: Any, **subprocess_kwrd: Any
    ) -> Generator[None]:
        """Invokes shell using subprocess.run"""
        if cmd_opts is None:
            cmd_opts = []
        capman = request.config.pluginmanager.getplugin("capturemanager")
        capman.suspend_global_capture(in_=True)
        print("\n\nDEBUG: CAPTURE DISABLED")
        yield
        print("\nPYTEST SYSTEM SHELL STARTED")
        subprocess.run([shell, *cmd_opts], *subprocess_args, **subprocess_kwrd)
        print("\n\nPYTEST SYSTEM SHELL EXIT")
        capman.resume_global_capture()

    return runner


def cli_name() -> str:
    return APP_NAME


def project_root() -> Path:
    """Returns project's root directory."""
    return Path(__file__).parent.parent


def cli_result(
    cmd_opts: list[str],
    sudo: bool = False,
    fake_time: str | None = None,
    launcher: str | list[str] | None = None,
) -> dict[str, Any]:
    """Invokes cli with given comand line options
    Captures and returns return code, stdout and stderr.
    """
    cli_cmd: str | list[str] | None = launcher

    if cli_cmd is None:
        cli_cmd = os.environ.get("PYTEST_CLI_CMD")

    if cli_cmd is None:
        cli_cmd = os.path.join(project_root(), cli_name())

    if isinstance(cli_cmd, str):
        cli_cmd = [cli_cmd]

    cmd = [*cli_cmd, *cmd_opts]

    if fake_time is not None:
        cmd_str = f"eval $(python-libfaketime); FAKETIME='{fake_time}' {' '.join(cmd)}"
        cmd = ["sh", "-c", cmd_str]

    if sudo is True:
        cmd.insert(0, "sudo")

    res = subprocess.run(
        cmd,
        capture_output=True,
    )

    stdout = res.stdout.decode(sys.stdout.encoding)
    stderr = res.stderr.decode(sys.stdout.encoding)
    # fmt: off
    return {
        "retcode": res.returncode,
        "stdout":  stdout,
        "stderr":  stderr,
        "cmd":     cmd
    }
    # fmt: on


def snapshot_cli_result(
    snapshot_tool: Any,
    cmd_opts: list[str],
    sudo: bool = False,
    context: str | None = None,
    **kwrd: Any,
) -> Generator[dict[str, Any]]:
    """Invokes cli with given comand line options, captures output, and asserts against snapshot."""
    res = cli_result(cmd_opts, sudo, **kwrd)
    retcode, stdout, stderr, cmd = itemgetter("retcode", "stdout", "stderr", "cmd")(res)

    output = [
        f"CMD: {' '.join(cmd)}",
        f"RETCODE={retcode}",
        "STDOUT:\n=======",
        stdout,
        "-------------------------------------------------------------",
        "STDERR:\n=======",
        stderr,
        "-------------------------------------------------------------",
    ]

    if context is not None:
        output.insert(0, f"CONTEXT: {context}")

    output = "\n".join(output)

    yield res
    assert output == snapshot_tool


def sudo_unlink(filename: str) -> None:
    res = subprocess.run(["sudo", "rm", filename], capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.decode(sys.stdout.encoding))
