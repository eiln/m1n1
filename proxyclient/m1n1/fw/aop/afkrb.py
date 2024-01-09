# SPDX-License-Identifier: MIT
import struct
from ..common import *
from ...utils import *

AFKRingBufItem = Struct(
    "magic" / PaddedString(4, "utf8"),
    "size" / Hex(Int32ul),
    #"channel" / Hex(Int32ul), # truncated EPIC header
    #"type" / EPICType,
)

# macos reserves first block in ringbuf for r/w pointers
"""        bufsize      unk
00000000  00007e80 00070006 00000000 00000000 00000000 00000000 00000000 00000000
00000020  00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000040  *   rptr
00000080  00000600 00000000 00000000 00000000 00000000 00000000 00000000 00000000
000000a0  00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
000000c0  *   wptr
00000100  00000680 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000120  00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000140  *
"""

class AOPAFKRingBuf(Reloadable):
    BLOCK_SIZE = 0x40
    BLOCK_COUNT = 3

    def __init__(self, ep, base, size):
        self.ep = ep
        self.base = base

        bs, unk = struct.unpack("<II", self.read_buf(0, 8))
        assert (bs + self.BLOCK_COUNT * self.BLOCK_SIZE * 2) == size
        self.bufsize = bs
        self.rptr = 0
        self.wptr = 0

    def read_buf(self, off, size):
        return self.ep.iface.readmem(self.base + off, size)

    def write_buf(self, off, data):
        return self.ep.iface.writemem(self.base + off, data)

    def get_rptr(self):
        return self.ep.asc.p.read32(self.base + self.BLOCK_SIZE)

    def get_wptr(self): # wptr offset was +0x80 in 12.3
        return struct.unpack("<I", self.read_buf(0x100, 4))[0]

    def update_rptr(self, rptr):
        self.write_buf(0x80, struct.pack("<I", rptr))
        self.ep.asc.p.write32(self.base + self.BLOCK_SIZE, rptr)

    def update_wptr(self, wptr):
        self.write_buf(0x100, struct.pack("<I", wptr))
        self.ep.asc.p.write32(self.base + 2 * self.BLOCK_SIZE, wptr)

    def read(self):
        self.wptr = self.get_wptr()

        stride = self.BLOCK_COUNT * self.BLOCK_SIZE * 2
        #chexdump(self.read_buf(0, self.bufsize))
        #chexdump32(self.read_buf(0, stride))
        while self.wptr != self.rptr:
            hdr = self.read_buf(stride + self.rptr, 0x10)
            item = AFKRingBufItem.parse(hdr)
            assert item.magic in ["IOP ", "AOP "]
            self.rptr += 0x10

            if (item.size > (self.bufsize - self.rptr)):
                hdr = self.read_buf(stride, 0x10)
                item = AFKRingBufItem.parse(hdr)
                self.rptr = 0x10
                assert magic in ["IOP ", "AOP "]

            payload = self.read_buf(stride + self.rptr, item.size)
            self.rptr = (align_up(self.rptr + item.size, self.BLOCK_SIZE * 2)) % self.bufsize
            self.update_rptr(self.rptr)
            yield hdr[8:] + payload
            self.wptr = self.get_wptr()

        self.update_rptr(self.rptr)

    def write(self, data):
        stride = self.BLOCK_COUNT * self.BLOCK_SIZE * 2

        self.rptr = self.get_rptr()

        if self.wptr < self.rptr and self.wptr + 0x10 >= self.rptr:
            raise AFKError("Ring buffer is full")

        hdr2, data = data[:8], data[8:]
        hdr = struct.pack("<4sI", b"IOP ", len(data)) + hdr2
        self.write_buf(stride + self.wptr, hdr)

        if len(data) > (self.bufsize - self.wptr - 0x10):
            if self.rptr < 0x10:
                raise AFKError("Ring buffer is full")
            self.write_buf(stride, hdr)
            self.wptr = 0

        if self.wptr < self.rptr and self.wptr + 0x10 + len(data) >= self.rptr:
            raise AFKError("Ring buffer is full")

        self.write_buf(stride + self.wptr + 0x10, data)
        self.wptr = align_up(self.wptr + 0x10 + len(data), self.BLOCK_SIZE * 2) % self.bufsize

        self.update_wptr(self.wptr)
        return self.wptr
