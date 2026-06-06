import os
from collections.abc import Callable
from typing import Any


def pytest_unwrap(fn: Any) -> Callable[..., Any]:
    """Extract the original function from a pytest-wrapped fixture.

    Needed when fixtures must be called as regular functions
    (e.g., inside @patch decorators at module scope).
    """
    return fn.__pytest_wrapped__.obj


def bt_linux_sample_01_unwrapped() -> str:
    """Get the bt_sample_01 path without needing fixture injection.

    Used in @patch decorators at module/class scope where fixture injection
    is not possible.
    """
    samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bt_linux", "data_samples")
    return os.path.join(samples_dir, "bt_sample_01")
