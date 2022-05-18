"""This module contains the main classes used in binread."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from struct import unpack
from typing import Any, Callable, Dict, Tuple, Union, Optional
import sys


try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


ByteOrder = Literal["little", "big", "native"]
"""Specifies the endiannes. `native` equals `sys.byteorder`."""


class NotEnoughBytes(Exception):
    def __init__(self, msg: str = "not enough bytes") -> None:
        super().__init__(msg)


class FieldType(ABC):
    """Abstract base class of all field types. Can be used to create a custom field type.

    Args:
       byteorder: specifies the endiannes of this type.
       to: specifies a callable to transform the extracted data.
    """

    def __init__(
        self,
        byteorder: ByteOrder = "native",
        to: Optional[Callable] = None,
    ):
        self._byteorder: ByteOrder = byteorder
        self.to = to

    @abstractmethod
    def extract(self, data: bytes, fields: Dict[str, Any]) -> Tuple[Any, int]:
        """Extracts the required bytes to construct this field.

        Args:
            data: The buffer to read.
            fields: Any previous read fields used as context.

        Returns:
            (Any, int): The field value that is constructed and the bytes read.

        Raises:
            NotEnoughBytes: If not enough bytes are provided to construct this field.

        """
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
        self._fields: dict[str, FieldType] = {}

        for name, field in fields.items():
            if isinstance(field, FieldType):
                self._fields[name] = field
            elif (
                isinstance(field, type)
                and issubclass(field, FieldType)
                and field != FieldType
            ):
                self._fields[name] = field()  # type: ignore
            elif hasattr(field, "_field_type"):
                self._fields[name] = getattr(field, "_field_type")
            else:
                raise Exception(f"unknown field type '{field}' with key '{name}'")

    def extract(self, data: bytes, fields: Dict[str, Any]) -> Tuple[Any, int]:
        value, bytes_read = self.read(data, allow_leftover=True, return_bytes=True)
        return value, bytes_read  # type: ignore

    def read(
        self, data: bytes, allow_leftover: bool = False, return_bytes: bool = False
    ) -> Dict[str, Any]:
        result = {}
        total = 0
        for name, field in self._fields.items():
            result[name], bytes_read = field.read_field(data, result)
            data = data[bytes_read:]
            total += bytes_read

        if len(data) != 0 and not allow_leftover:
            raise Exception("left over bytes")

        if return_bytes:
            return result, total  # type: ignore
        else:
            return result


def format(cls: type) -> type:


    fields = {}
    for name, field in cls.__dict__.items():
        if _is_field_type(field):
            fields[name] = field

    for name in fields.keys():
        cls.__annotations__[name] = Any

    cls = dataclass(cls)

    fmt = Format(fields)
    setattr(cls, "_field_type", fmt)

    @staticmethod
    def read(*args, **kwargs):
        field_dict = fmt.read(*args, **kwargs)
        return cls(**field_dict)

    setattr(cls, "read", read)

    return cls


def _is_field_type(obj: Any) -> bool:
    return (
        isinstance(obj, FieldType)
        or (isinstance(obj, type) and issubclass(obj, FieldType))
        or hasattr(obj, "_field_type")
    )
