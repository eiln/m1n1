# SPDX-License-Identifier: MIT
import time
from construct import *
from ..afk.epic import *
from .afkrb import *
from .ipc import *

# RX report handlers
def report_handler(message, reptype):
    def f(x):
        x.is_report = True
        x.message = message
        x.reptype = reptype
        return x
    return f

i8 = Int8sl
u8 = Int8ul
i16 = Int16sl
u16 = Int16ul
i32 = Int32sl
u32 = Int32ul
i64 = Int64sl
u64 = Int64ul

EPICSubHeaderVer2 = Struct(
    "length" / Int32ul,
    "version" / Default(Int8ul, 2),
    "category" / EPICCategory,
    "type" / Hex(Int16ul),
    "timestamp" / Default(Int64ul, 0),
    "unk1" / Default(Hex(Int32ul), 0),
    "unk2" / Default(Hex(Int32ul), 0),
)

AOPEPICHeader = Struct(
    # ringbuf header
    # "magic" / PaddedString(4, "utf8"),
    # "size" / Hex(Int32ul),
    "header" / EPICHeader,
    "subheader" / EPICSubHeaderVer2,
)

AOPHelloReport = Struct(
    "name" / PaddedString(0x10, "ascii"),
    "unk0" / Hex(u32),
    "unk1" / Hex(u32),
    "retcode" / Hex(u32), # 0xE00002C2
    "unk3" / Hex(u32),
    "channel" / Hex(u32),
    "unk5" / Hex(u32),
    "unk6" / Hex(u32),
)
assert(AOPHelloReport.sizeof() == 0x2c)

class AOPEPICEndpoint(AFKRingBufEndpoint):
    RBCLS = AOPAFKRingBuf
    BUFSIZE = 0x1000

    def __init__(self, *args, **kwargs):
        self.chan = 0x0
        self.seq = 0x0
        self.wait_reply = False
        self.ready = False
        super().__init__(*args, **kwargs)

        self.reporthandler = {}
        self.reporttypes = {}
        for name in dir(self):
            i = getattr(self, name)
            if not callable(i):
                continue
            if not getattr(i, "is_report", False):
                continue
            self.reporthandler[i.message] = i
            self.reporttypes[i.message] = i.reptype

    def handle_report(self, hdr, sub, fd):
        handler = self.reporthandler.get(sub.type, None)
        if handler is None:
            self.log("unknown report: 0x%x" % (sub.type))
            return False

        payload = fd.read()
        reptype = self.reporttypes.get(sub.type, None)
        try:
            rep = reptype.parse(payload)
        except Exception as e:
            self.log("failed to parse report 0x%x" % (sub.type))
            self.log(e)
            rep = None
            chexdump(payload)
            self.log("size: 0x%x vs 0x%x" % (len(payload), reptype.sizeof()))
        return handler(hdr, sub, fd, rep)

    def handle_reply(self, hdr, sub, fd):
        if self.wait_reply:
            self.pending_call.read_resp(fd)
            self.wait_reply = False
            return True
        return False

    @report_handler(0xc0, AOPHelloReport)
    def handle_hello(self, hdr, sub, fd, rep):
        self.chan = rep.channel
        self.log(f"Hello! (name: {rep.name}, chan: {rep.channel:#x})")
        self.ready = True
        return True

    def handle_ipc(self, data):
        fd = BytesIO(data)
        header = AOPEPICHeader.parse_stream(fd)
        hdr, sub = header.header, header.subheader

        handled = False
        if sub.category == EPICCategory.REPORT:
            handled = self.handle_report(hdr, sub, fd)
        if sub.category == EPICCategory.REPLY:
            handled = self.handle_reply(hdr, sub, fd)

        self.log(f"< 0x{hdr.channel:x} Type {hdr.type} Ver {hdr.version} Tag {hdr.seq}")
        self.log(f"  Len {sub.length} Ver {sub.version} Cat {sub.category} Type {sub.type:#x} Ts {sub.timestamp:#x}")
        chexdump(fd.read())

        return handled

    def indirect(self, call, timeout=0.1):
        tx = call.ARGS.build(call.args)
        self.asc.iface.writemem(self.txbuf, tx[4:])

        cmd = self.roundtrip(IndirectCall(
            txbuf=self.txbuf_dva, txlen=len(tx) - 4,
            rxbuf=self.rxbuf_dva, rxlen=self.BUFSIZE,
            retcode=0,
        ), category=EPICCategory.COMMAND, typ=call.TYPE, timeout=timeout)
        fd = BytesIO()
        fd.write(struct.pack("<I", cmd.rets.retcode))
        fd.write(self.asc.iface.readmem(self.rxbuf, cmd.rets.rxlen))
        fd.seek(0)
        call.read_resp(fd)
        return call

    def roundtrip(self, call, timeout=0.3, category=EPICCategory.NOTIFY, typ=None):
        tx = call.ARGS.build(call.args)
        hdr = AOPEPICHeader.build(Container(
            header=Container(
                channel=self.chan,
                type=EPICType.NOTIFY,
                version=2,
                seq=self.seq,
            ),
            subheader=Container(
                length=len(tx),
                category=category,
                type=typ or call.TYPE,
            ),
        ))
        self.pending_call = call
        self.wait_reply = True
        self.send_ipc(hdr + tx)

        deadline = time.time() + timeout
        while time.time() < deadline and self.wait_reply:
            self.asc.work()
        if self.wait_reply:
            self.wait_reply = False
            raise ASCTimeout("ASC reply timed out")

        return call

class AOPSPUEndpoint(AOPEPICEndpoint): # SPUApp.t / i2c.pp.t
    SHORT = "spu"

class AOPAccelEndpoint(AOPEPICEndpoint):
    SHORT = "accel"

class AOPGyroEndpoint(AOPEPICEndpoint):
    SHORT = "gyro"

    def start_queues(self):
        pass  # don't init gyro ep (we don't have one)

class AOPALSEndpoint(AOPEPICEndpoint): # als.hint
    SHORT = "als"

    @report_handler(0xc4, ALSLuxReport)
    def handle_lux(self, hdr, sub, fd, rep):
        self.log(rep)
        return True

class AOPWakehintEndpoint(AOPEPICEndpoint): # wakehint
    SHORT = "wakehint"

class AOPUNK26Endpoint(AOPEPICEndpoint):
    SHORT = "unk26"

class AOPAudioEndpoint(AOPEPICEndpoint): # aop-audio.rigger
    SHORT = "audio"

class AOPVoiceTriggerEndpoint(AOPEPICEndpoint): # aop-voicetrigger
    SHORT = "voicetrigger"
