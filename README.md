<h1 align="center">Binread</h1>
 
 <h3 align="center">
Parse any binary format 📖
</h3>
<br> 
 
<p align="center">
<a href="https://github.com/remopas/binread/issues"><img src="https://img.shields.io/github/issues/remopas/binread"></a>
<a href="https://pypi.org/project/binread/"><img src="https://img.shields.io/pypi/l/binread"></a>
<a href="https://pypi.org/project/binread/"><img src="https://img.shields.io/pypi/dm/binread"></a>
</p>
  

## Installation

```
pip install binread
```

## Usage

Just create a class with each field representing a certain data-type and decorate it with `format`, then pass some bytes to `<cls>.read()`:

```python

from binread import Format, U16, Array, format

data = open('example.bin', 'rb').read()

@format
class Fmt:
  field0 = U16,
  field1 = Array(U16, length=5)

print(Fmt.read(data))
# Fmt(field0=16, field1=[1, 2, 3, 4, 5])
```
Or create a dictionary mapping for each field and it's type and construct a `Format` object.
```python

fmt = Format({
  "field0": U16,
  "field1": Array(U16, length=5)
})

print(fmt.read(data))
# {
#   "field0": 16,
#   "field1": [1, 2, 3, 4, 5]
# }
```

`Format.read()` expects a `bytes` object and by default raises an exception if there are bytes left over. Set `allow_leftover=True` to disable this behaviour. If leftover bytes are allowed, the number of bytes that where read can be inspected with `return_bytes=True`.

### Arrays

Other than supporting fixed length arrays with passing an integer to `length`, binread supports multiple techniques of defining variable length arrays.

Using a previously defined field in the same `Format`.
```python
Format({
  "length_key": U16,
  "array": Array(U8, length="length_key"
})
```

Using a function or lambda (with access to previously defined fields as a `dict`)
```python
Format({
  "length_key": U16,
  "array": Array(U8, length=lambda x: x["length_key"] + 1
})
```

When specifying `length_bytes` instead of `length` the bytes are counted instead of the elements.
```python
Format({
  "length_key": U16,
  "array": Array(String(length=7, encoding='ascii'), length_bytes="length_key"
})
```

When dealing with a terminated array, `terminator` can be used to define when to stop.
```python
fmt = Format({
  "array": Array(U8, terminator=b'\x00'
})
```
The terminator is checked at the first byte or the byte immediately after an element.

### Nested Formats

The `Format` type can be used a in another `Format` or `Array` just as any other type.
```python
Format({
  "field1": I32,
  "nested_format": Format({
    "field1": U64
  })
})

Format({
  "array": Array(Format({
    "field1": Bool,
    "field2": Char,
  }), length=4)
})
```

### Byte Order

Any field type accepts a `byteorder` value in it's constructor, which can be `little`, `big` or `native` (default).

**No** padding or alignment is done at all. For packing C structures with padding and alignment see [struct](https://docs.python.org/3/library/struct.html)

### Supported Types

Binread supports the following types

- Structural: `Array` and `Format`
- Signed integers: `I8`, `I16`, `I32`, `I64`
- Unsigned Integers: `U8`, `U16`, `U32`, `U64`
- Floats: `F16`, `F32`, `F64`
- Misc: `Char`, `String`, `Bool`, `Tuple`
