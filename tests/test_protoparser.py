import unittest
import struct
import json

from resappserver.protoparser import *

class FakeBytestream:
    def __init__(self, bytearray_):
        self._pos = 0
        self._bytearray = bytearray_
    def recv(self, bytes_number):
        buf = self._bytearray[self._pos : self._pos + bytes_number]
        print(buf, len(self._bytearray))
        self._pos += bytes_number
        return buf

class GoodInputCheck(unittest.TestCase):
    testjson = ['foo', {'bar': 1.0}]
    testjson_str = json.dumps(testjson)
    cases = [
        {
            'format' : '=BihIs[I]',
            'test_fields' : ['field1', 'field2', 'field3', 'field4', 'field5'],
            'test_values' : [2, -555322, -4872, 4572, 'qwerty'],
            'test_bytearray' : struct.pack('=BihII6s', 2, -555322, -4872, 4572, 6, bytes('qwerty', 'utf-8')),
        },
        {
            'format' : '=Bs[I]&i&',
            'subparsers' : [JsonProtoParser(), JsonProtoParser()],
            'test_fields' : ['field1', 'field2', 'field3', 'field4', 'field5'],
            'test_values' : [2, 'qwerty', testjson, 12345, testjson],
            'test_bytearray' : struct.pack('=BI6sI{}siI{}s'.format(len(testjson_str), len(testjson_str)), \
                                           2, 6, bytes('qwerty', 'utf-8'), len(testjson_str), \
                                           bytes(testjson_str, 'utf-8'), 12345, len(testjson_str), bytes(testjson_str, 'utf-8')),
        }
    ]

    def test_cases(self):
        for case in self.cases:
            subparsers = case['subparsers'] if 'subparsers' in case else None
            case_result = {field : val for field, val in zip(case['test_fields'], case['test_values'])}
            p = AdvancedStructProtoParser(case['format'], case['test_fields'], subparsers)
            print(case['test_bytearray'])
            parsed_result = p.parse(FakeBytestream(case['test_bytearray']))
            self.assertEqual(case_result, parsed_result)

if __name__ == 'main':
    unittest.main()