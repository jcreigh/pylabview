from struct import *

class BinaryStream:
    def __init__(self, base_stream, byteOrder="LE"):
        self.base_stream = base_stream
        self.byteOrder = byteOrder

    def readByte(self):
        return self.base_stream.read(1)

    def readBytes(self, length=9999999):
        return self.base_stream.read(length)

    def readChar(self, byteOrder=None):
        return self.unpack('b', byteOrder=byteOrder)

    def readUChar(self, byteOrder=None):
        return self.unpack('B', byteOrder=byteOrder)

    def readBool(self, byteOrder=None):
        return self.unpack('?', byteOrder=byteOrder)

    def readInt16(self, byteOrder=None):
        return self.unpack('h', 2, byteOrder=byteOrder)

    def readUInt16(self, byteOrder=None):
        return self.unpack('H', 2, byteOrder=byteOrder)

    def readInt32(self, byteOrder=None):
        return self.unpack('i', 4, byteOrder=byteOrder)

    def readUInt32(self, byteOrder=None):
        return self.unpack('I', 4, byteOrder=byteOrder)

    def readInt64(self, byteOrder=None):
        return self.unpack('q', 8, byteOrder=byteOrder)

    def readUInt64(self, byteOrder=None):
        return self.unpack('Q', 8, byteOrder=byteOrder)

    def readFloat(self, byteOrder=None):
        return self.unpack('f', 4, byteOrder=byteOrder)

    def readDouble(self, byteOrder=None):
        return self.unpack('d', 8, byteOrder=byteOrder)

    def readString(self, byteOrder=None):
        length = self.readUInt16()
        return self.unpack(str(length) + 's', length, byteOrder=byteOrder)

    def writeBytes(self, value):
        self.base_stream.write(value)

    def writeChar(self, value):
        self.pack('c', value)

    def writeUChar(self, value):
        self.pack('C', value)

    def writeBool(self, value):
        self.pack('?', value)

    def writeInt16(self, value):
        self.pack('h', value)

    def writeUInt16(self, value):
        self.pack('H', value)

    def writeInt32(self, value):
        self.pack('i', value)

    def writeUInt32(self, value):
        self.pack('I', value)

    def writeInt64(self, value):
        self.pack('q', value)

    def writeUInt64(self, value):
        self.pack('Q', value)

    def writeFloat(self, value):
        self.pack('f', value)

    def writeDouble(self, value):
        self.pack('d', value)

    def writeString(self, value):
        length = len(value)
        self.writeUInt16(length)
        self.pack(str(length) + 's', value)

    def __len__(self):
        return self.base_stream.len

    def pack(self, fmt, data):
        return self.writeBytes(pack(fmt, data))

    def unpack(self, fmt, length=1, byteOrder="LE"):
        byteOrder = byteOrder or self.byteOrder
        return unpack(("<" if byteOrder == "LE" else ">") + fmt, self.readBytes(length))[0]
