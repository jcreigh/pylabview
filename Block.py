from PIL import Image
from hashlib import md5
from zlib import decompress
from LVmisc import getVersion
from StringIO import StringIO
from binstreamer import BinaryStream
from LVmisc import LABVIEW_COLOR_PALETTE

class Block(object):
    def __init__(self, vi, header):
        self.vi = vi
        self.header = header
        self.name = header['Name']
        self.count = header['Count']
        self.vi.reader.seek(header['Offset'])
        self.ints = []
        self.ints.append(self.vi.reader.readInt32())
        self.ints.append(self.vi.reader.readInt32())
        self.ints.append(self.vi.reader.readInt32())
        self.offset = \
            self.vi.header['DataSet']['Offset'] + self.vi.reader.readUInt32()
        self.ints.append(self.vi.reader.readInt32())
        self.size = None

    def getData(self, blockNr=0, useCompression=False):
        if self.size is None:
            minSize = self.vi.header['DataSet']['Size']
            for i in self.vi.blocks_arr:
                if self != i and i.offset > self.offset:
                    minSize = min(minSize, i.offset - self.offset)
            self.size = minSize
            size = sumSize = 0
            self.raw_data = []
            for i in range(0, blockNr + 1):
                if size % 4 > 0:
                    size += 4 - (size % 4)
                sumSize += size
                self.vi.reader.seek(self.offset + sumSize)
                size = self.vi.reader.readUInt32()
                sumSize += 4
                if (sumSize + size) > self.size:
                    raise IOError("Out of block/container data (%d + %d) %d"
                        % (sumSize, size, self.size))
                self.vi.reader.seek(self.offset + sumSize)
                data = self.vi.reader.read(size)
                self.raw_data.append(data)
        data = BinaryStream(StringIO(self.raw_data[blockNr]))
        if useCompression:
            size = len(data) - 4
            if size < 2:
                raise IOError("Unable to decompress section [%s:%d]: \
                            block-size-error - size: %d" % (self.name, blockNr, size))
            usize = data.readInt32("BE")
            if (usize < size) or usize > size * 10:
                raise IOError("Unable to decompress section [%s:%d]: \
                            uncompress-size-error - size: %d - uncompress-size: %d"
                            % (self.name, blockNr, size, usize))
            data = BinaryStream(StringIO(decompress(data.read(size))))
        return data

class LVSR(Block):
    def __init__(self, *args):
        return Block.__init__(self, *args)

    def getData(self, *args):
        block = Block.getData(self, *args)
        self.version = getVersion(block.readUInt32())
        self.INT1 = block.readInt16()
        self.flags = block.readUInt16()
        self.protected = ((self.flags & 0x2000) > 0)
        self.flags = self.flags & 0xDFFF
        return block

class vers(Block):
    def __init__(self, *args):
        return Block.__init__(self, *args)

    def getData(self, *args):
        block = Block.getData(self, *args)
        self.version = getVersion(block.readUInt32())
        self.version_text = block.read("s1")
        self.version_info = block.read("s1")
        return block

class icl8(Block):
    def __init__(self, *args):
        return Block.__init__(self, *args)

    def getData(self, *args):
        return Block.getData(self, *args)

    def loadIcon(self, bitsPerPixel=8):
        icon = Image.new("RGB", (32, 32))
        block = self.getData()
        for y in range(0, 32):
            for x in range(0, 32):
                idx = block.readByte()
                icon.putpixel((x, y), LABVIEW_COLOR_PALETTE[idx])
        self.icon = icon
        return icon

class BDPW(Block):
    def __init__(self, *args):
        return Block.__init__(self, *args)

    def getData(self, *args):
        block = Block.getData(self, *args)
        self.password_md5 = block.read(16)
        self.hash_1 = block.read(16)
        self.hash_2 = block.read(16)
        return block

class LIBN(Block):
    def __init__(self, *args):
        return Block.__init__(self, *args)

    def getData(self, *args):
        block = Block.getData(self, *args)
        self.count = block.readUInt32()
        self.content = block.read("s1")
        return block

class BDH(Block):
    def __init__(self, *args):
        return Block.__init__(self, *args)

    def getData(self, *args):
        Block.getData(self, *args)
        block = Block.getData(self, useCompression=True)
        self.content = block.read("s4", "BE")
        self.hash = md5(self.content).digest()
        return block

BDHc = BDHb = BDH
