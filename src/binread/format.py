from abc import ABC, abstractmethod
from struct import unpack
from typing import Any, Callable, Dict, Tuple, Union
import sys

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


ByteOrder = Literal["little", "big", "native"]


class NotEnoughBytes(Exception):
    def __init__(self, msg: str = "not enough bytes") -> None:
        super().__init__(msg)


class FieldType(ABC):
    def __init__(
        self,
        byteorder: ByteOrder = "native",
        to: Union[Callable, None] = None,
    ):
        self._byteorder: ByteOrder = byteorder
        self.to = to

    @abstractmethod
    def extract(self, data: bytes, fields: Dict[str, Any]) -> Tuple[Any, int]:
        pass

    def read_field(self, data: bytes, fields: Dict[str, Any]) -> Tuple[Any, int]:
        value, size = self.extract(data, fields)

        if self.to:
            value = self.to(value)

        return value, size

    def byteorder(self) -> Literal["little", "big"]:
        if self._byteorder == "little" or self._byteorder == "big":
            return self._byteorder
        else:
            return sys.byteorder


class Integer(FieldType):
    def __init__(
        self,
        size: int,
        signed: bool,
        byteorder: ByteOrder = "native",
        to: Union[Callable, None] = None,
    ):
        super().__init__(byteorder, to)
        self.signed = signed
        self._size = size

    def extract(self, data: bytes, fields: Dict[str, Any]):
        if self._size > len(data):
            raise NotEnoughBytes()

        return (
            int.from_bytes(data[: self._size], self.byteorder(), signed=self.signed),
            self._size,
        )


class Float(FieldType):
    def __init__(
        self,
        size: Literal[2, 4, 8],
        byteorder: ByteOrder = "native",
        to: Union[Callable, None] = None,
    ):
        super().__init__(byteorder, to)
        self._size = size

    def extract(self, data: bytes, fields: Dict[str, Any]) -> Tuple[Any, int]:
        if self._size > len(data):
            raise NotEnoughBytes()

        byteorder = self.byteorder()
        if byteorder == "little":
            char = "<"
        else:
            char = ">"

        if self._size == 2:
            char += "e"
        elif self._size == 4:
            char += "f"
        elif self._size == 8:
            char += "d"
        else:
            raise Exception("invalid float size, must be either 2, 4 or 8")

        return *unpack(char, data[: self._size]), self._size


class Format(FieldType):
    def __init__(self, fields: Dict[str, Union[FieldType, type]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields: dict[str, FieldType] = {}

        for name, field in fields.items():
            if isinstance(field, FieldType):
                self.fields[name] = field
            elif issubclass(field, FieldType) and field != FieldType:
                self.fields[name] = field()  # type: ignore

    def extract(self, data: bytes, fields: Dict[str, Any]) -> Tuple[Any, int]:
        value, bytes_read = self.read(data, allow_leftover=True, return_bytes=True)
        return value, bytes_read  # type: ignore

    def read(
        self, data: bytes, allow_leftover: bool = False, return_bytes: bool = False
    ) -> Dict[str, Any]:
        result = {}
        total = 0
        for name, field in self.fields.items():
            result[name], bytes_read = field.read_field(data, result)
            data = data[bytes_read:]
            total += bytes_read

        if len(data) != 0 and not allow_leftover:
            raise Exception("left over bytes")

        if return_bytes:
            return result, total # type: ignore
        else:
            return result
