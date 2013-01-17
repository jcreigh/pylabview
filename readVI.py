#!/usr/bin/python

import types
from binstreamer import BinaryStream
from Block import *
from LVmisc import StrToHex
from hashlib import md5

class VI():
    def __init__(self, fn):
        self.fn = fn
        self.fh = open(self.fn, "rb")
        self.reader = BinaryStream(self.fh, byteOrder="BE")

        self.readVI()

    def readVI(self):
        reader = self.reader
        lastPos = -1
        curPos = 0
        header = {}
        while lastPos != curPos:
            lastPos = curPos
            reader.seek(curPos)
            #print curPos
            header['id1'] = reader.read(6)
            header['id2'] = reader.readInt16()
            header['id3'] = reader.read(4)
            header['id4'] = reader.read(4)
            if header['id1'] != "RSRC\r\n":
                raise IOError("Wrong File Format: Missing header 1")
            if header['id3'] != "LVIN":
                raise IOError("Wrong File Format: Missing header 3")
            if header['id4'] != "LBVW":
                raise IOError("Wrong File Format: Missing header 4")
            header['RSRCOffset'] = reader.readUInt32()
            header['RSRCSize'] = reader.readUInt32()
            #print header['RSRCOffset'], header['RSRCSize']
            if header['RSRCOffset'] >= 0 and header['RSRCSize'] >= 0:
                curPos = header['RSRCOffset']
            else:
                raise IOError("Wrong RSRC-Header")

        header['DataSetOffset'] = reader.readUInt32()
        header['DataSetSize'] = reader.readUInt32()
        header['DataSetInt1'] = reader.readUInt32()
        header['DataSetInt2'] = reader.readUInt32()
        header['DataSetInt3'] = reader.readUInt32()

        header['BlockInfoOffset'] = header['RSRCOffset'] + reader.readUInt32()
        header['BlockInfoSize'] = reader.readUInt32()

        self.header = header

        reader.seek(header['BlockInfoOffset'])

        blockInfoCount = reader.readUInt32() + 1
        if blockInfoCount > 1000:
            raise IOError("VI.BlockInfoCount too large?")

        blocks_arr = []
        blocks = {}
        for i in range(0, blockInfoCount):
            blocks_arr.append(Block(self))
            blocks[blocks_arr[-1].name] = blocks_arr[-1]

        self.blocks = blocks
        self.blocks_arr = blocks_arr

        for i in range(0, blockInfoCount):
            blocks_arr[i].getData()

    def getBlockIdByBlockName(self, name):
        for i in range(0, len(self.blockInfo)):
            if self.blockInfo[i]['BlockName'] == name:
                return i
        return None

    def get(self, name, forceRaw=False):
        if name in globals() and not forceRaw:
            if isinstance(globals()[name], types.ClassType):
                return globals()[name](self)
        if name in self.blocks:
                return self.blocks[name]
        return None

    def calcPassword(self, newPassword=""):
        LVSR = self.get("LVSR")
        LIBN = self.get("LIBN")
        BDH = self.get("BDH")

        md5Password = md5(newPassword).digest()
        md5Hash1 = md5(md5Password + LIBN.content + LVSR.raw).digest()
        md5Hash2 = md5(md5Hash1 + BDH.hash).digest()

        out = {}
        out['password'] = newPassword
        out['password_md5'] = md5Password
        out['hash_1'] = md5Hash1
        out['hash_2'] = md5Hash2
        self.m_password_set = out


if __name__ == "__main__":
    n = "test2.vi"
    import sys
    if len(sys.argv) > 1:
        n = sys.argv[1]
    vi = VI("testVIs/" + n)
    for i in vi.blocks_arr:
        print i.name
    #t = vi.getBlockContentById(vi.getBlockIdByBlockName("BDPW"))
    #open("dumps/" + n + ".dmp", "w").write(t.base_stream.read())
    #vi.getIcon().save('tmp.png')
    print "password md5: " + StrToHex(vi.get("BDPW").password_md5)
    print "hash_1      : " + StrToHex(vi.get("BDPW").hash_1)
    print "hash_2      : " + StrToHex(vi.get("BDPW").hash_2)
    vi.calcPassword("")
    print "password md5: " + StrToHex(vi.m_password_set['password_md5'])
    print "hash_1      : " + StrToHex(vi.m_password_set['hash_1'])
    print "hash_2      : " + StrToHex(vi.m_password_set['hash_2'])
    print vi.get("vers").version
    print vi.get("LVSR").version
    #vi.Icon.icon.save("out.png")

