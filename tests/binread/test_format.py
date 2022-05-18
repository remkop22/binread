from dataclasses import dataclass
import unittest
import binread


class TestFormat(unittest.TestCase):

    def test_format_class(self):
        @binread.formatclass
        class FormatExample:
            field1 = binread.U8
            field2 = binread.U16

        FormatExample.read(b"\x00\xFF\x00")
