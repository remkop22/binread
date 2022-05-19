"""This module contains the main classes used in binread."""

from io import RawIOBase
from .reader import ByteOrder, ByteReader
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, SupportsBytes, Union, Optional


try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


class FieldType(ABC):
    """Abstract base class of all field types. Can be used to create a custom field type.

    Args:
       byteorder: specifies the endianness of this type.
       to: specifies a callable to transform the extracted data.
    """

    def __init__(
        self,
        byteorder: Optional[ByteOrder] = None,
        to: Optional[Callable] = None,
    ):
        self.byteorder: Optional[ByteOrder] = byteorder
        self.default_byteorder: ByteOrder = "native"
        self.to = to

    @abstractmethod
    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> Any:
        pass

    def read_field(self, data: ByteReader, fields: Dict[str, Any]) -> Any:
        value = self.extract(data, fields)

        if self.to:
            value = self.to(value)

        return value

    def inheriting_byteorder(self) -> ByteOrder:
        if self.byteorder:
            return self.byteorder
        else:
            return self.default_byteorder

    @staticmethod
    def to_instance(field: Union["FieldType", type]) -> Optional["FieldType"]:
        if isinstance(field, FieldType):
            return field
        elif (
            isinstance(field, type)
            and issubclass(field, FieldType)
            and field != FieldType
        ):
            return field()  # type: ignore
        elif hasattr(field, "_field_type"):
            return getattr(field, "_field_type")
        else:
            return None


class Integer(FieldType):
    def __init__(self, size: int, signed: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signed = signed
        self.size = size

    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> int:
        return data.read_integer(
            self.size, self.byteorder or self.default_byteorder, self.signed
        )


class Float(FieldType):
    def __init__(self, size: Literal[2, 4, 8], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size: Literal[2, 4, 8] = size

    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> float:
        return data.read_float(self.size, self.byteorder or self.default_byteorder)


class Format(FieldType):
    def __init__(self, fields: Dict[str, Union[FieldType, type]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields: dict[str, FieldType] = {}

        byteorder = self.inheriting_byteorder()

        for name, field in fields.items():
            field = self.to_instance(field)

            if not field:
                raise Exception(f"unknown field type '{field}' with key '{name}'")

            field.default_byteorder = byteorder
            self.fields[name] = field

    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> Dict[str, Any]:
        return self.read(data, allow_leftover=True)

    def read(
        self,
        byte_data: Union[ByteReader, RawIOBase, bytes, SupportsBytes],
        allow_leftover: bool = False,
        return_bytes: bool = False,
    ) -> Dict[str, Any]:
        result = {}

        if not isinstance(byte_data, ByteReader):
            data = ByteReader(byte_data)
        else:
            data = byte_data

        start_pos = data.tell()

        for name, field in self.fields.items():
            result[name] = field.read_field(data, result)

        if (not data.is_eof()) and (not allow_leftover):
            raise Exception("left over bytes")

        if return_bytes:
            return result, data.tell() - start_pos  # type: ignore
        else:
            return result


class FormatClass(Format):
    def __init__(self, cls: type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cls = cls

    def read(self, *args, **kwargs) -> Dict[str, Any]:
        result = super().read(*args, **kwargs)

        if isinstance(result, tuple):
            result, bytes_read = result
            return self._cls(**result), bytes_read  # type: ignore
        else:
            return self._cls(**result)


def formatclass(*args, **kwargs):
    with_args = True

    if len(args) == 1 and isinstance(args[0], type):
        with_args = False
        kwargs = {}
        cls = args[0]
        args = []

    def decorator(cls) -> type:
        fields = {}
        for name, field in cls.__dict__.items():
            field = FieldType.to_instance(field)

            if field:
                fields[name] = field

        for name in fields.keys():
            cls.__annotations__[name] = Any

        dataclass_args = kwargs.get("dataclass_args", {})

        cls = dataclass(**dataclass_args)(cls)

        fmt = FormatClass(cls, fields, *args, **kwargs)
        setattr(cls, "_field_type", fmt)

        @staticmethod
        def read(*args, **kwargs):
            return fmt.read(*args, **kwargs)

        setattr(cls, "read", read)

        return cls

    if with_args:
        return decorator
    else:
        return decorator(cls)
