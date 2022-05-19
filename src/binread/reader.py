from abc import ABC, abstractmethod
from io import BytesIO, RawIOBase
from typing import SupportsBytes, Union
from struct import unpack
import sys


try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

ByteOrder = Literal["little", "big", "native"]


def normalize_byteorder(byteorder: ByteOrder) -> Literal["little", "big"]:
    if byteorder == "native":
        return sys.byteorder
    else:
        return byteorder


class NotEnoughBytes(Exception):
    def __init__(self, msg: str = "not enough bytes") -> None:
        super().__init__(msg)


class ByteReader(ABC):
    def __init__(self, data: Union[bytes, SupportsBytes, RawIOBase]):
        if isinstance(data, RawIOBase):
            self.data = data
        elif isinstance(data, bytes):
            self.data = BytesIO(data)
        elif isinstance(data, SupportsBytes):
            self.data = BytesIO(data.__bytes__())

    def tell(self) -> int:
        return self.data.tell()

    def is_eof(self) -> bool:
        current_pos = self.tell()
        self.data.seek(0, 2)
        end_pos = self.tell()
        self.data.seek(current_pos)
        return current_pos >= end_pos

    def read_integer(self, size: int, byteorder: ByteOrder, signed: bool) -> int:
        return int.from_bytes(
            self.read_bytes(size), normalize_byteorder(byteorder), signed=signed
        )

    def read_float(self, size: Literal[2, 4, 8], byteorder: ByteOrder) -> float:
        byteorder = normalize_byteorder(byteorder)

        if byteorder == "little":
            char = "<"
        else:
            char = ">"

        if size == 2:
            char += "e"
        elif size == 4:
            char += "f"
        elif size == 8:
            char += "d"
        else:
            raise Exception("invalid float size, must be either 2, 4 or 8")

        return unpack(char, self.read_bytes(size))[0]

    def read_bytes(self, size: int) -> bytes:
        data = self.data.read(size)
        if (not data) or (len(data) != size):
            raise NotEnoughBytes()
        return data
