class BluetoothDevice:
    """Representation of bluetooth device

    Properties:
        klass (str)
        mac (str)
        name (str)
        pairing_key (str)
        adapter_mac (str)
        source (str): kind of 'Windows', 'Linux'
        pairing_type (str): kind of 'LinkKey', 'LongTermKey'
        pairing_data (dict): pairing key data fields

    """

    mac: str | None
    name: str | None
    pairing_key: str | None
    adapter_mac: str | None
    klass: str | None
    source: str | None
    pairing_type: str | None
    pairing_data: dict[str, str]

    def __init__(
        self,
        mac: str | None = None,
        name: str | None = None,
        pairing_key: str | None = None,
        adapter_mac: str | None = None,
        device_class: str | None = None,
        source: str | None = None,
        pairing_type: str | None = None,
        pairing_data: dict[str, str] | None = None,
    ) -> None:
        if pairing_type is None and pairing_key is not None:
            pairing_type = self.pairing_type_link_key()

        pairing_data = {} if pairing_data is None else dict(pairing_data)

        if pairing_key is not None and "Key" not in pairing_data:
            pairing_data["Key"] = pairing_key

        # fmt: off
        self.source         = source
        self.klass          = device_class
        self.mac            = mac
        self.name           = name
        self.pairing_key    = pairing_key
        self.adapter_mac    = adapter_mac
        self.pairing_type   = pairing_type
        self.pairing_data   = pairing_data
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

    @classmethod
    def pairing_type_link_key(cls) -> str:
        return "LinkKey"

    @classmethod
    def pairing_type_long_term_key(cls) -> str:
        return "LongTermKey"

    def is_source_linux(self) -> bool:
        return self.source == "Linux"

    def is_source_windows(self) -> bool:
        return self.source == "Windows"

    def is_pairing_type_long_term_key(self) -> bool:
        return self.pairing_type == self.pairing_type_long_term_key()

    def pairing_fingerprint(self) -> tuple[str | None, tuple[tuple[str, str], ...]]:
        """Compare pairing data between two devices (replaces simple pairing_key comparison)"""
        return (
            self.pairing_type,
            tuple(sorted((k, str(v)) for k, v in self.pairing_data.items())),
        )
