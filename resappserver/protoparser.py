import struct
import json
from abc import ABC, abstractmethod

class ProtoParser(ABC):
    """
    ProtoParser provides an interface for parsing a byte array conforming to some protocol.
    It is assumed that a dictionary {'field_name': value} is returned by parse() function.
    """

    """
    It is assumed that a dictionary {'field_name': value} is returned.
    """
    @abstractmethod
    def parse(self, bytestream):
        pass

class StructProtoParser(ProtoParser):
    """
    Implements ProtoParser interface for module struct functons.
    """
    def __init__(self, format_, fieldnames):
        self.struct_ = struct.Struct(format_)
        self.fieldnames = fieldnames

    def parse(self, bytestream):
        buf = bytestream.recv(self.struct_.size)
        fieldsdata = self.struct_.unpack(buf)
        parsed_data = {fieldname : fielddata for fieldname, fielddata in zip(self.fieldnames, fieldsdata)}
        return parsed_data

class StringProtoParser(ProtoParser):
    """
    Implements ProtoParser interface for strings with the "prepended" number of characters
    """
    def __init__(self, byteorder, characters_number_type, fieldname):
        self._byteorder = byteorder
        self._characters_number_type = characters_number_type
        self._fieldname = fieldname

    def set_fieldname(self, fieldname):
        self._fieldname = fieldname

    def parse(self, bytestream):
        format_ = '{}{}'.format(self._byteorder, self._characters_number_type)
        buf = bytestream.recv(struct.calcsize(format_))
        characters_number, = struct.unpack(format_, buf)
        buf = bytestream.recv(characters_number)
        format_ = '{}{}s'.format(self._byteorder, characters_number)
        str_, = struct.unpack(format_, buf)
        parsed_data = {self._fieldname : str(str_, encoding='utf-8'),}
        return parsed_data

class JsonProtoParser(StringProtoParser):
    """
    Implements ProtoParser interface for JSON which is a string parsed by StringProtoParser
    """
    def __init__(self, byteorder='', characters_number_type='I', fieldname=None):
        super().__init__(byteorder, characters_number_type, fieldname)

    def set_fieldname(self, fieldname):
        self._fieldname = fieldname

    def set_byteorder(self, byteorder):
        self._byteorder = byteorder

    def parse(self, bytestream):
        json_dict = super().parse(bytestream)
        json_dict[self._fieldname] = json.loads(json_dict[self._fieldname])
        return json_dict
        
class AdvancedStructProtoParser(ProtoParser):
    """
    StructProtoParser parses a byte array following struct module specification.
    It only adds to the format string, which should be passes to __init__(),
    two things:
    (1) strings with the "prepended" number of characters: 's[I]' which means that
    the bytearray contains the number of characters of type I and after that the string s
    with the corresponding number of characters.
    (2) custom types for which appropriate ProtoParser must be passed: '&'. 
    Example:
    format_ = 'hhls[I]&&'
    subparsers = [JsonProtoParser(), AnotherProtoParser()]
    """
    def __init__(self, format_, fieldnames, subparsers = None):
        self._pipeline = []
        fieldnames_buf = []
        format_iter = iter(format_)
        byteorder = ''
        c = next(format_iter)
        if c == '=' or c == '<' or c == '>' or c == '!':
            byteorder = c
        buf = byteorder
        fieldnames = list(fieldnames)
        fieldnames.reverse()
        if subparsers is not None:
            subparsers = list(subparsers)
            subparsers.reverse()
        def dump_buffer():
            if buf != byteorder:
                self._pipeline.append(StructProtoParser(buf, fieldnames_buf))
            return byteorder, []
        for c in format_iter:
            if len(fieldnames) == 0:
                raise BadParserFormat('Number of field names does not match with that in the format string')
            if c == 's':
                buf, fieldnames_buf = dump_buffer()
                next(format_iter)
                characters_number_type = next(format_iter)
                next(format_iter)
                self._pipeline.append(StringProtoParser(byteorder, characters_number_type, fieldnames.pop()))
            elif c == '&':
                if (subparsers is None) or (len(subparsers) == 0):
                    raise BadParserFormat('Number of subparsers does not match with that in the format string')
                buf, fieldnames_buf = dump_buffer()
                subparser = subparsers.pop()
                subparser.set_fieldname(fieldnames.pop())
                subparser.set_byteorder(byteorder)
                self._pipeline.append(subparser)
            else:
                buf += c
                fieldnames_buf.append(fieldnames.pop())
        dump_buffer()

    def parse(self, bytestream):
        parsed_data = {}
        for parser in self._pipeline:
            parsed_data.update(parser.parse(bytestream))
        return parsed_data

class BadParserFormat(Exception):
    pass