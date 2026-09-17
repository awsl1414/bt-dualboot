from importlib.metadata import version

# CLI entry-point name (see [project.scripts] in pyproject.toml).
# Package distribution name on PyPI is bt-dualboot-ng.
APP_NAME: str = "bt-dualboot"
__version__: str = version("bt-dualboot-ng")
