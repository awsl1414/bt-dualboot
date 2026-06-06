class BluetoothDevice:
    """Representation of bluetooth device

    Properties:
        klass (str)
        mac (str)
        name (str)
        pairing_key (str)
        adapter_mac (str)
        source (str): kind of 'Windows', 'Linux'

    """

    mac: str | None
    name: str | None
    pairing_key: str | None
    adapter_mac: str | None
    klass: str | None
    source: str | None

    def __init__(
        self,
        mac: str | None = None,
        name: str | None = None,
        pairing_key: str | None = None,
        adapter_mac: str | None = None,
        device_class: str | None = None,
        source: str | None = None,
    ) -> None:
        # fmt: off
        self.source         = source
        self.klass          = device_class
        self.mac            = mac
        self.name           = name
        self.pairing_key    = pairing_key
        self.adapter_mac    = adapter_mac
        # fmt: on

    def __repr__(self) -> str:
        source = "?"
        if self.source is not None:
            source = self.source[0]
        return f"{self.__class__} {source} [{self.mac}] {self.name}"

    @classmethod
    def source_linux(cls) -> str:
        return "Linux"

    @classmethod
    def source_windows(cls) -> str:
        return "Windows"

    def is_source_linux(self) -> bool:
        return self.source == "Linux"

    def is_source_windows(self) -> bool:
        return self.source == "Windows"
