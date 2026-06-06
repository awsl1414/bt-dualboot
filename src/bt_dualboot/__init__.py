from importlib.metadata import metadata, version

APP_NAME: str = metadata("bt-dualboot")["Name"]
__version__: str = version("bt-dualboot")
