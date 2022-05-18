from .format import Integer, FieldType, Float
from typing import Any, Callable, Iterable, Tuple as TupleType, Type, Union, Dict


class U8(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(1, False, *args, **kwargs)


class I8(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(1, True, *args, **kwargs)


class U16(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(2, False, *args, **kwargs)


class I16(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(2, True, *args, **kwargs)


class U32(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(4, False, *args, **kwargs)


class I32(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(4, True, *args, **kwargs)


class U64(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(8, False, *args, **kwargs)


class I64(Integer):
    def __init__(self, *args, **kwargs):
        super().__init__(8, True, *args, **kwargs)


class F16(Float):
    def __init__(self, *args, **kwargs):
        super().__init__(2, *args, **kwargs)


class F32(Float):
    def __init__(self, *args, **kwargs):
        super().__init__(4, *args, **kwargs)


class F64(Float):
    def __init__(self, *args, **kwargs):
        super().__init__(8, *args, **kwargs)


class Bool(U8):
    def extract(self, data: bytes, fields: Dict[str, Any]):
        value, bytes_read = super().extract(data, fields)
        return bool(value), bytes_read


class Char(U8):
    def extract(self, data: bytes, fields: Dict[str, Any]):
        value, bytes_read = super().extract(data, fields)
        return chr(value), bytes_read


class Array(FieldType):
    def __init__(
        self,
        element: Union[FieldType, Type[FieldType]],
        length: Union[int, str, Callable[[Dict[str, Any]], int], None] = None,
        length_bytes: Union[int, str, Callable[[Dict[str, Any]], int], None] = None,
        terminator: Union[bytes, None] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if self._byteorder:
            byteorder = self._byteorder
        else:
            byteorder = self._default_byteorder

        if isinstance(element, FieldType):
            element._default_byteorder = byteorder
            self.element = element
        elif issubclass(element, FieldType) and element != FieldType:
            element_instance = element()
            element_instance._default_byteorder = byteorder
            self.element = element_instance
        else:
            raise Exception(f"invalid array element {element}")

        self._length = length
        self._length_bytes = length_bytes
        self._terminator = terminator

    def length(self, fields: Dict[str, Any]) -> int:
        if isinstance(self._length, int):
            return self._length
        elif isinstance(self._length, str):
            return fields[self._length]
        elif isinstance(self._length, Callable):
            return self._length(fields)
        else:
            raise Exception(f"invalid length specifier '{self._length}'")

    def length_bytes(self, fields: Dict[str, Any]) -> int:
        if isinstance(self._length_bytes, int):
            return self._length_bytes
        elif isinstance(self._length_bytes, str):
            return fields[self._length_bytes]
        elif isinstance(self._length_bytes, Callable):
            return self._length_bytes(fields)
        else:
            raise Exception(f"invalid length specifier '{self._length}'")

    def extract_with_length(
        self, data: bytes, fields: Dict[str, Any], length: int
    ) -> TupleType[Any, int]:
        result = [None] * length
        total = 0
        for i in range(length):
            result[i], bytes_read = self.element.read_field(data, {})
            data = data[bytes_read:]
            total += bytes_read
        return result, total

    def extract_with_terminator(
        self, data: bytes, fields: Dict[str, Any], terminator: bytes
    ) -> TupleType[Any, int]:
        result = []
        total = 0

        while not data.startswith(terminator):
            value, bytes_read = self.element.read_field(data, {})
            result.append(value)
            data = data[bytes_read:]
            total += bytes_read

        total += len(terminator)

        return result, total

    def extract_with_length_bytes(
        self, data: bytes, fields: Dict[str, Any], length_bytes: int
    ) -> TupleType[Any, int]:
        result = []
        total = 0
        while total < length_bytes:
            value, bytes_read = self.element.read_field(data, {})
            result.append(value)
            data = data[bytes_read:]
            total += bytes_read
        return result, total

    def extract(self, data: bytes, fields: Dict[str, Any]) -> TupleType[Any, int]:
        if self._length is not None:
            length = self.length(fields)
            return self.extract_with_length(data, fields, length)
        elif self._terminator is not None:
            return self.extract_with_terminator(data, fields, self._terminator)
        elif self._length_bytes:
            length_bytes = self.length_bytes(fields)
            return self.extract_with_length_bytes(data, fields, length_bytes)
        else:
            raise Exception(
                "array must either have a length, length_bytes or a terminator"
            )


class Tuple(FieldType):
    def __init__(self, fields: Iterable[Union[FieldType, type]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fields = []

        for field in fields:
            if isinstance(field, FieldType):
                self._fields.append(field)
            elif (
                isinstance(field, type)
                and issubclass(field, FieldType)
                and field != FieldType
            ):
                self._fields.append(field())  # type: ignore
            elif hasattr(field, "_field_type"):
                self._fields.append(getattr(field, "_field_type"))
            else:
                raise Exception(f"unknown field type '{field}'")

        self._fields: TupleType[FieldType] = tuple(self._fields)

    def extract(self, data: bytes, fields: Dict[str, Any]) -> TupleType[Any, int]:
        result = [None] * len(self._fields)
        total = 0

        for i, field in enumerate(self._fields):
            result[i], bytes_read = field.read_field(data, fields)
            data = data[bytes_read:]
            total += bytes_read

        return result, total


class String(Array):
    def __init__(
        self,
        *args,
        encoding: str = "utf-8",
        **kwargs,
    ):
        super().__init__(U8, *args, **kwargs)
        self.encoding = encoding

    def extract(self, data: bytes, fields: Dict[str, Any]) -> TupleType[Any, int]:
        value, bytes_read = super().extract(data, fields)
        return bytes(value).decode(self.encoding), bytes_read
