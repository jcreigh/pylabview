from PIL import Image
from hashlib import md5
from zlib import decompress
from LVmisc import getVersion
from StringIO import StringIO
from binstreamer import BinaryStream
from LVmisc import LABVIEW_COLOR_PALETTE

class Block(object):
    def __init__(self, vi):
        self.vi = vi
        self.name = self.vi.reader.read(4)
        self.count = self.vi.reader.readUInt32() + 1
        self._infoOffset = self.vi.header['BlockInfoOffset'] + self.vi.reader.readUint32()
        tmp_pos = self.vi.reader.tell()
        self.vi.reader.seek(self._infoOffset)
        self.ints = []
        self.ints.append(self.vi.reader.readInt32())
        self.ints.append(self.vi.reader.readInt32())
        self.ints.append(self.vi.reader.readInt32())
        self._offset = \
            self.vi.header['DataSetOffset'] + self.vi.reader.readUInt32()
        self.ints.append(self.vi.reader.readInt32())
        self.vi.reader.seek(tmp_pos)
        self.size = None

    def getData(self, blockNr=0, useCompression=False):
        if self.size is None:
            minSize = self.vi.header['DataSetSize']
            #print minSize
            for i in self.vi.blocks_arr:
                if self != i and i._offset > self._offset:
                    #print i.name, self.name, i._offset, self._offset
                    minSize = min(minSize, i._offset - self._offset)
                    #print minSize
            self.size = minSize
            size = sumSize = 0
            self.raw_data = []
            #print "|", self._offset
            #print "%", self.count
            for i in range(0, blockNr + 1):
                if size % 4 > 0:
                    size += 4 - (size % 4)
                sumSize += size
                #print "!", self._offset + sumSize
                self.vi.reader.seek(self._offset + sumSize)
                size = self.vi.reader.readUInt32()
                sumSize += 4
                if (sumSize + size) > self.size:
                    raise IOError("Out of block/container data (%d + %d) %d"
                        % (sumSize, size, self.size))
                self.vi.reader.seek(self._offset + sumSize)
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
        #print "|", data
        return data

class LVSR():
    def __init__(self, vi):
        self.vi = vi
        block = vi.blocks["LVSR"].getData()
        self.raw = block.read()
        block.seek(0)
        self.version = getVersion(block.readUInt32("BE"))
        self.INT1 = block.readInt16()
        self.flags = block.readUInt16()
        self.protected = ((self.flags & 0x2000) > 0)
        self.flags = self.flags & 0xDFFF

class vers():
    def __init__(self, vi):
        self.vi = vi
        block = vi.blocks["vers"].getData()
        self.version = getVersion(block.readUInt32("BE"))
        self.version_text = block.read("s1")
        self.version_info = block.read("s1")

class Icon():
    def __init__(self, vi):
        self.vi = vi
        self.loadIcon()

    def loadIcon(self, bitsPerPixel=8):
        icon = Image.new("RGB", (32, 32))
        block = self.vi.blocks["vers"].getData()
        if "icl8" not in self.vi.blocks:
            raise IOError("No icon (%d bits/pixel) found in file" % bitsPerPixel)
        color = []
        for i in range(0, 256):
            c = LABVIEW_COLOR_PALETTE[i]
            r = c & 0xFF
            g = (c >> 8) & 0xFF
            b = (c >> 16) & 0xFF
            color.append((r, g, b, 0 if i == 0 else 255))
        for y in range(0, 32):
            for x in range(0, 32):
                idx = block.readByte()
                icon.putpixel((x, y), color[idx])
        self.icon = icon
        return icon

class BDPW():
    def __init__(self, vi):
        self.vi = vi
        block = vi.blocks["BDPW"].getData()
        self.password_md5 = block.read(16)
        self.hash_1 = block.read(16)
        self.hash_2 = block.read(16)
        #print self.password_md5, "|", self.hash_1, "|", self.hash_2, "|"


class LIBN():
    def __init__(self, vi):
        self.vi = vi
        self.count = 0
        self.content = ""
        if "LIBN" in vi.blocks:
            block = vi.blocks["LIBN"].getData()
            if len(block) > 0:
                self.count = block.readUInt32()
                self.content = block.read("s1")

class BDH():
    def __init__(self, vi):
        BDH_id = "BDHc"
        if BDH_id not in vi.blocks:
            BDH_id = "BDHb"
        block = vi.blocks[BDH_id].getData(useCompression=True)
        self.raw = block.read()
        block.seek(0)
        self.content = block.read("s4", "BE")
        self.hash = md5(self.content).digest()
