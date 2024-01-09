# SPDX-License-Identifier: MIT
import time
from construct import *
from ..afk.epic import *
from .afkrb import *
from .ipc import *

class AOPEPICEndpoint(AFKRingBufEndpoint):
    RBCLS = AOPAFKRingBuf
    BUFSIZE = 0x1000

    def __init__(self, *args, **kwargs):
        self.chan = 0x0
        self.seq = 0x0
        self.wait_reply = False
        self.ready = False
        super().__init__(*args, **kwargs)

    def handle_hello(self, hdr, sub, fd):
        if sub.type != 0xc0:
            return False
        payload = fd.read()
        name = payload.split(b"\0")[0].decode("ascii")
        self.log(f"Hello! (endpoint {name})")
        self.ready = True
        return True

    def handle_reply(self, hdr, sub, fd):
        if self.wait_reply:
            self.pending_call.read_resp(fd)
            self.wait_reply = False
            return True
        return False

    def handle_ipc(self, data):
        fd = BytesIO(data)
        hdr = EPICHeader.parse_stream(fd)
        sub = EPICSubHeaderVer2.parse_stream(fd)

        handled = False
        if sub.category == EPICCategory.REPORT:
            handled = self.handle_hello(hdr, sub, fd)
            self.chan = hdr.channel
        if sub.category == EPICCategory.REPLY:
            handled = self.handle_reply(hdr, sub, fd)

        self.log(f"< 0x{hdr.channel:x} Type {hdr.type} Ver {hdr.version} Tag {hdr.seq}")
        self.log(f"  Len {sub.length} Ver {sub.version} Cat {sub.category} Type {sub.type:#x} Ts {sub.timestamp:#x}")
        self.log(f"  Unk1 {sub.unk1:#x} Unk2 {sub.unk2:#x}")
        chexdump(fd.read())

        return handled

    def indirect(self, call, timeout=0.1):
        tx = call.ARGS.build(call.args)
        self.asc.iface.writemem(self.txbuf, tx[4:])

        cmd = self.roundtrip(IndirectCall(
            txbuf=self.txbuf_dva, txlen=len(tx) - 4,
            rxbuf=self.rxbuf_dva, rxlen=self.BUFSIZE,
            retcode=0,
        ), category=EPICCategory.COMMAND, typ=call.TYPE)
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

class AOPWakehintEndpoint(AOPEPICEndpoint): # wakehint
    SHORT = "wakehint"

class AOPUNK26Endpoint(AOPEPICEndpoint):
    SHORT = "unk26"

class AOPAudioEndpoint(AOPEPICEndpoint): # aop-audio.rigger
    SHORT = "audio"

class AOPVoiceTriggerEndpoint(AOPEPICEndpoint): # aop-voicetrigger
    SHORT = "voicetrigger"
