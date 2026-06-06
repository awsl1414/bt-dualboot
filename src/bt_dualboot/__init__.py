from importlib.metadata import metadata, version

APP_NAME = metadata("bt-dualboot")["Name"]
__version__ = version("bt-dualboot")
