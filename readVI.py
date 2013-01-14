#!/usr/bin/python

from binary import BinaryStream
from StringIO import StringIO
from constants import LABVIEW_VERSION_STAGE, LABVIEW_COLOR_PALETTE
from PIL import Image
from hashlib import md5
from zlib import decompress

class VI():
    def __init__(self, fn):
        self.fn = fn
        self.fh = open(self.fn, "rb")
        self.freader = BinaryStream(self.fh, False)

        self.readVI()
        self.readLVSR()
        self.readvers()
        self.readBDPW()

    def readVI(self):
        self.fh.seek(0)
        freader = self.freader
        lastPos = -1
        curPos = 0
        fileHeader = {}
        while lastPos != curPos:
            lastPos = curPos
            self.fh.seek(curPos)
            #print curPos
            fileHeader['id1'] = freader.readBytes(6)
            fileHeader['id2'] = freader.readInt16()
            fileHeader['id3'] = freader.readBytes(4)
            fileHeader['id4'] = freader.readBytes(4)
            if fileHeader['id1'] != "RSRC\r\n":
                raise IOError("Wrong File Format: Missing header 1")
            if fileHeader['id3'] != "LVIN":
                raise IOError("Wrong File Format: Missing header 3")
            if fileHeader['id4'] != "LBVW":
                raise IOError("Wrong File Format: Missing header 4")
            fileHeader['RSRCOffset'] = freader.readUInt32()
            fileHeader['RSRCSize'] = freader.readUInt32()
            #print fileHeader['RSRCOffset'], fileHeader['RSRCSize']
            if fileHeader['RSRCOffset'] >= 0 and fileHeader['RSRCSize'] >= 0:
                curPos = fileHeader['RSRCOffset']
            else:
                raise IOError("Wrong RSRC-Header")

        fileHeader['DataSetOffset'] = freader.readUInt32()
        fileHeader['DataSetSize'] = freader.readUInt32()
        fileHeader['DataSetInt'] = freader.readUInt32()
        fileHeader['DataSetInt'] = freader.readUInt32()
        fileHeader['DataSetInt'] = freader.readUInt32()

        fileHeader['BlockInfoOffset'] = fileHeader['RSRCOffset'] + freader.readUInt32()
        fileHeader['BlockInfoSize'] = freader.readUInt32()

        self.fh.seek(fileHeader['BlockInfoOffset'])

        blockInfoCount = freader.readUInt32() + 1
        if blockInfoCount > 1000:
            raise IOError("VI.BlockInfoCount too large?")

        blockInfo = []
        for i in range(0, blockInfoCount):
            blockInfo.append({})
            blockInfo[i]['BlockName'] = freader.readBytes(4)
            blockInfo[i]['BlockCount'] = freader.readUInt32() + 1
            blockInfo[i]['BlockInfoOffset'] = fileHeader['BlockInfoOffset'] + freader.readUInt32()

        for i in range(0, blockInfoCount):
            self.fh.seek(blockInfo[i]['BlockInfoOffset'])
            blockInfo[i]['INT1'] = freader.readInt32()
            blockInfo[i]['INT2'] = freader.readInt32()
            blockInfo[i]['INT3'] = freader.readInt32()
            blockInfo[i]['BlockOffset'] = fileHeader['DataSetOffset'] + freader.readUInt32()
            blockInfo[i]['INT4'] = freader.readInt32()

        for i in range(0, blockInfoCount):
            minSize = fileHeader['DataSetSize']
            for j in range(0, blockInfoCount):
                if i != j:
                    deltaSize = blockInfo[j]['BlockOffset'] - blockInfo[i]['BlockOffset']
                    if deltaSize > 0 and deltaSize < minSize:
                        minSize = deltaSize
            blockInfo[i]['BlockFileSize'] = minSize
        self.fileHeader = fileHeader
        self.blockInfo = blockInfo

    def getBlockIdByBlockName(self, name):
        for i in range(0, len(self.blockInfo)):
            if self.blockInfo[i]['BlockName'] == name:
                return i
        return None

    def getBlockContentById(self, blockID, blockNr=0, useCompression=False):
        freader = self.freader
        blockNr = max(0, blockNr)
        if blockID is None:
            return BinaryStream(StringIO(""))
        #print "---"
        #print self.blockInfo[blockID]
        #print "---"
        offset = self.blockInfo[blockID]['BlockOffset']
        size = sumSize = 0
        for i in range(0, blockNr + 1):
            if size % 4 > 0:
                size = size + (4 - (size % 4))
            sumSize += size
            self.fh.seek(offset)
            size = freader.readUInt32()
            sumSize += 4
            if (sumSize + size) > self.blockInfo[blockID]['BlockFileSize']:
                raise IOError("Out of block/container data (%d + %d) %d" % (sumSize, size, self.blockInfo[blockID]['BlockFileSize']))

        #print "blockNr: %d\noffset: %d\nsize: %d\nsumSize: %d" % (blockNr, offset, size, sumSize)
        self.fh.seek(offset + sumSize)
        blockData = BinaryStream(StringIO(self.fh.read(size)))
        if useCompression:
            size = blockData.base_stream.len - 4
            if size < 2:
                raise IOError("Unable to decompress section [#%d]: block-size-error - size: %d" % (blockID, size))
            usize = blockData.readInt32("BE")
            if (usize < size) or usize > size * 10:
                raise IOError("Unable to decompress section [#%d]: uncompress-size-error - size: %d - uncompress-size: %d" % (blockID, size, usize))
            ucdata = decompress(blockData.readBytes(size))
            blockData = BinaryStream(StringIO(ucdata))

        return blockData

    def getBlockContentByName(self, name, blockNr=0, useCompression=False):
        blockID = self.getBlockIdByBlockName(name)
        return self.getBlockContentById(blockID, blockNr, useCompression)

    def readLVSR(self):
        versID = self.getBlockIdByBlockName("LVSR")
        block = self.getBlockContentById(versID)
        out = {}
        out['version'] = self._getVersion(block.readUInt32("BE"))
        out['INT1'] = block.readInt16()
        out['flags'] = block.readUInt16()
        out['protected'] = ((out['flags'] & 0x2000) > 0)
        out['flags'] = out['flags'] & 0xDFFF
        self.m_LVSR = out

    def readvers(self):
        versID = self.getBlockIdByBlockName("vers")
        block = self.getBlockContentById(versID)
        out = self._getVersion(block.readUInt32("BE"))
        length = block.readChar()
        out['version_text'] = block.readBytes(length)
        length = block.readChar()
        out['version_info'] = block.readBytes(length)
        self.m_version = out

    def _getVersion(self, vcode):
        ver = {}
        ver['major'] = ((vcode >> 28) & 0x0F) * 10 + ((vcode >> 24) & 0x0F)
        ver['minor'] = (vcode >> 20) & 0x0F
        ver['bugfix'] = (vcode >> 16) & 0x0F
        ver['stage'] = (vcode >> 13) & 0x07
        ver['flags'] = (vcode >> 8) & 0x1F  # 5 bit??
        ver['build'] = ((vcode >> 4) & 0x0F) * 10 + ((vcode >> 0) & 0x0F)
        ver['stage_text'] = LABVIEW_VERSION_STAGE[0]
        if ver['stage'] < len(LABVIEW_VERSION_STAGE):
            ver['stage_text'] = LABVIEW_VERSION_STAGE[ver['stage']]
        return ver

    def getIcon(self, bitsPerPixel=8):
        icon = Image.new("RGB", (32, 32))
        icon_id = self.getBlockIdByBlockName("icl8")
        if icon_id < 0:
            raise IOError("No icon (%d bits/pixel) found in file" % bitsPerPixel)
        icon_content = self.getBlockContentById(icon_id)
        color = []
        for i in range(0, 256):
            c = LABVIEW_COLOR_PALETTE[i]
            r = c & 0xFF
            g = (c >> 8) & 0xFF
            b = (c >> 16) & 0xFF
            color.append((r, g, b, 0 if i == 0 else 255))
        for y in range(0, 32):
            for x in range(0, 32):
                idx = icon_content.readChar()
                icon.putpixel((x, y), color[idx])
        self.m_icon = icon
        return icon

    def readBDPW(self):
        content = self.getBlockContentByName("BDPW")
        out = {}
        out['password_md5'] = content.readBytes(16)
        out['hash_1'] = content.readBytes(16)
        out['hash_2'] = content.readBytes(16)
        self.m_password = out

    def calcPassword(self, newPassword=""):
        LVSR_content = self.getBlockContentByName("LVSR")
        LIBN_content = self.getBlockContentByName("LIBN")
        BDH_id = "BDHc"
        if self.getBlockIdByBlockName("BDHc") < 0:
            BDH_id = "BDHb"
        BDH_content = self.getBlockContentByName(BDH_id, useCompression=True)
        md5Password = md5(newPassword).digest()

        LIBN_count = LIBN_len = 0
        if len(LIBN_content) != 0:
            LIBN_count = LIBN_content.readInt32()
            LIBN_count
            LIBN_len = LIBN_content.readChar()

        md5Hash1 = md5(md5Password + LIBN_content.readBytes(LIBN_len) + LVSR_content.base_stream.read()).digest()

        BDH_len = BDH_content.readInt32()
        BDH_hash = md5(BDH_content.readBytes(BDH_len)).digest()

        md5Hash2 = md5(md5Hash1 + BDH_hash).digest()

        out = {}
        out['password'] = newPassword
        out['password_md5'] = md5Password
        out['hash_1'] = md5Hash1
        out['hash_2'] = md5Hash2
        self.m_password_set = out

def StrToHex(x, sep=" "):
    return str.join(sep, [("0" + hex(ord(a))[2:])[-2:] for a in x])

if __name__ == "__main__":
    n = "test2.vi"
    import sys
    if len(sys.argv) > 1:
        n = sys.argv[1]
    vi = VI("testVIs/" + n)
    for i in vi.blockInfo:
        print i
    t = vi.getBlockContentById(vi.getBlockIdByBlockName("BDPW"))
    open("dumps/" + n + ".dmp", "w").write(t.base_stream.read())
    #vi.getIcon().save('tmp.png')
    vi.readBDPW()
    print "password md5: " + StrToHex(vi.m_password['password_md5'])
    print "hash_1      : " + StrToHex(vi.m_password['hash_1'])
    print "hash_2      : " + StrToHex(vi.m_password['hash_2'])
    vi.calcPassword("")
    print "password md5: " + StrToHex(vi.m_password_set['password_md5'])
    print "hash_1      : " + StrToHex(vi.m_password_set['hash_1'])
    print "hash_2      : " + StrToHex(vi.m_password_set['hash_2'])

