from binread.reader import ByteReader
from .format import Integer, FieldType, Float
from typing import Any, Callable, Iterable, List, Tuple as TupleType, Type, Union, Dict
from typing import SupportsBytes


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
    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> bool:
        return bool(super().extract(data, fields))


class Char(U8):
    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> str:
        return chr(super().extract(data, fields))


class Array(FieldType):
    def __init__(
        self,
        element: Union[FieldType, Type],
        length: Union[int, str, Callable[[Dict[str, Any]], int], None] = None,
        length_bytes: Union[int, str, Callable[[Dict[str, Any]], int], None] = None,
        terminator: Union[Any, None] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        element = self.to_instance(element)

        if not element:
            raise Exception(f"invalid array element {element}")

        element.default_byteorder = self.inheriting_byteorder()
        self.element = element

        self.length = length
        self.length_bytes = length_bytes
        self.terminator = terminator

    def get_length(self, fields: Dict[str, Any]) -> int:
        if isinstance(self.length, int):
            return self.length
        elif isinstance(self.length, str):
            return fields[self.length]
        elif isinstance(self.length, Callable):
            return self.length(fields)
        else:
            raise Exception(f"invalid length specifier '{self.length}'")

    def get_length_bytes(self, fields: Dict[str, Any]) -> int:
        if isinstance(self.length_bytes, int):
            return self.length_bytes
        elif isinstance(self.length_bytes, str):
            return fields[self.length_bytes]
        elif isinstance(self.length_bytes, Callable):
            return self.length_bytes(fields)
        else:
            raise Exception(f"invalid length specifier '{self.length_bytes}'")

    def extract_with_length(self, data: ByteReader, length: int) -> List[Any]:
        return [self.element.read_field(data, {}) for i in range(length)]

    def extract_with_terminator(self, data: ByteReader, terminator: Any) -> List[Any]:
        result = []

        while True:
            result.append(self.element.read_field(data, {}))

            if result[-1] == terminator:
                break

        return result

    def extract_with_length_bytes(
        self, data: ByteReader, length_bytes: int
    ) -> List[Any]:
        result = []
        start = data.tell()
        while (data.tell() - start) < length_bytes:
            result.append(self.element.read_field(data, {}))

        return result

    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> List[Any]:
        if self.length is not None:
            length = self.get_length(fields)
            return self.extract_with_length(data, length)
        elif self.terminator is not None:
            return self.extract_with_terminator(data, self.terminator)
        elif self.length_bytes is not None:
            length_bytes = self.get_length_bytes(fields)
            return self.extract_with_length_bytes(data, length_bytes)
        else:
            raise Exception(
                "array must either have a length, length_bytes or a terminator"
            )


class Bytes(Array):
    def __init__(
        self,
        length: Union[int, str, Callable[[Dict[str, Any]], int], None] = None,
        terminator: Union[bytes, None] = None,
        *args,
        **kwargs,
    ):
        super().__init__(U8, length, terminator=terminator, *args, **kwargs)

    def extract_with_length(self, data: ByteReader, length: int) -> bytes:
        return data.read_bytes(length)

    def extract_with_terminator(
        self,
        data: ByteReader,
        terminator: bytes,
    ) -> bytes:
        result = bytearray()

        while True:
            element = data.read_bytes(len(terminator))
            result += element
            if element == terminator:
                break

        return bytes(result)


class Tuple(FieldType):
    def __init__(self, fields: Iterable[Union[FieldType, type]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = []  # type: ignore
        byteorder = self.inheriting_byteorder()

        for field in fields:
            field = self.to_instance(field)

            if not field:
                raise Exception(f"unknown field type '{field}'")

            field.default_byteorder = byteorder
            self.fields.append(field)

        self._fields: TupleType[FieldType] = tuple(self._fields)

    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> TupleType[Any, ...]:
        result = [None] * len(self._fields)

        for i, field in enumerate(self._fields):
            result[i] = field.read_field(data, fields)

        return tuple(result)


class String(Bytes):
    def __init__(
        self,
        *args,
        encoding: str = "utf-8",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.encoding = encoding

    def extract(self, data: ByteReader, fields: Dict[str, Any]) -> str:
        value = super().extract(data, fields)
        return value.decode(self.encoding)  # type: ignore
