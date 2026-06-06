import os


def bt_linux_sample_01_unwrapped() -> str:
    """Get the bt_sample_01 path without needing fixture injection."""
    samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "infrastructure", "linux", "data_samples")
    return os.path.join(samples_dir, "bt_sample_01")
