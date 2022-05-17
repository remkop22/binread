from .format import Integer, FieldType, Float
from typing import Any, Tuple, Type, Union, Dict


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
        length: Union[int, str, None] = None,
        terminator: Union[bytes, None] = None,
        *args,
        **kwargs,
    ):
        if isinstance(element, FieldType):
            self.element = element
        elif issubclass(element, FieldType) and element != FieldType:
            self.element = element()
        else:
            raise Exception(f"invalid array element {element}")

        super().__init__(self.element._byteorder, *args, **kwargs)

        self._length = length
        self._terminator = terminator

    def length(self, fields: Dict[str, Any]) -> int:
        if isinstance(self._length, int):
            return self._length
        elif isinstance(self._length, str):
            return fields[self._length]
        else:
            raise Exception(f"invalid length specifier '{self._length}'")

    def extract_with_length(
        self, data: bytes, fields: Dict[str, Any], length: int
    ) -> Tuple[Any, int]:
        result = [None] * length
        total = 0
        for i in range(length):
            result[i], bytes_read = self.element.read(data, {})
            data = data[bytes_read:]
            total += bytes_read
        return result, total

    def extract_with_terminator(
        self, data: bytes, fields: Dict[str, Any], terminator: bytes
    ) -> Tuple[Any, int]:
        result = []
        total = 0

        while not data.startswith(terminator):
            value, bytes_read = self.element.read(data, {})
            result.append(value)
            data = data[bytes_read:]
            total += bytes_read

        total += len(terminator)
        print(total)

        return result, total

    def extract(self, data: bytes, fields: Dict[str, Any]) -> Tuple[Any, int]:
        if self._length is not None:
            length = self.length(fields)
            return self.extract_with_length(data, fields, length)
        elif self._terminator is not None:
            return self.extract_with_terminator(data, fields, self._terminator)
        else:
            raise Exception("array must either have a length or a terminator")
