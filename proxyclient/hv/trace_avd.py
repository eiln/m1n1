# SPDX-License-Identifier: MIT
from m1n1.trace import Tracer
from m1n1.trace.dart import DARTTracer
from m1n1.utils import *
from m1n1.proxyutils import RegMonitor
hv.p.hv_set_time_stealing(0, 1)

import datetime
import os
import struct
import time

AVD_BASE = 0x268000000
AVD_REGS = [
    #(0x1000000, 0x4000, "unk0"),
    #(0x1010000, 0x4000, "dart"),
    #(0x1002000, 0x1000, "unk2"),
    (0x1070000, 0x4000, "piodma"),
    #(0x1088000, 0x4000, "sram"),
    (0x108c000, 0xc000, "cmd"),
    #(0x1098000, 0x4000, "mbox"),
    #(0x10a3000, 0x1000, "unka"),
    (0x1100000, 0xc000, "config"),
    (0x110c000, 0x4000, "dma"),
    #(0x1400000, 0x4000, "wrap"),
]

class AVDTracer(Tracer):
    DEFAULT_MODE = TraceMode.SYNC

    def __init__(self, hv, dev_path, dart_tracer, verbose=False):
        super().__init__(hv, verbose=verbose, ident=type(self).__name__ + "@" + dev_path)
        self.dev = hv.adt[dev_path]
        self.dart_tracer = dart_tracer
        self.base = self.dev.get_reg(0)[0] # 0x268000000
        self.p = hv.p
        self.u = hv.u
        self.dart = dart_tracer.dart

        mon = RegMonitor(hv.u)
        #for (offset, size, name) in AVD_REGS: mon.add(self.base + offset, size, name=name)
        self.mon = mon

        iomon = RegMonitor(hv.u, ascii=True)
        iomon1 = RegMonitor(hv.u, ascii=True)
        def readmem_iova(addr, size, readfn=None):
            try:
                return dart_tracer.dart.ioread(0, addr, size)
            except Exception as e:
                print(e)
                return None
        iomon.readmem = readmem_iova
        def readmem_iova(addr, size, readfn=None):
            try:
                return dart_tracer.dart.ioread(1, addr, size)
            except Exception as e:
                print(e)
                return None
        iomon1.readmem = readmem_iova
        #iomon.add(0x4000, 0x4000, "dart-0-0x4000")
        #iomon.add(0x744000, 0x100, "dart-0-0x744000")
        self.iomon = iomon
        self.iomon1 = iomon1
        self.state_active = False
        self.outdir = ""

    def avd_r32(self, off): return self.p.read32(self.base + off)
    def avd_w32(self, off, x): return self.p.write32(self.base + off, x)
    def avd_r64(self, off): return self.p.read64(self.base + off)
    def avd_w64(self, off, x): return self.p.write64(self.base + off, x)

    def start(self):
        self.hv.add_tracer(irange(self.base + 0x1098004, 4), "avd-mbox-init", TraceMode.SYNC, self.evt_rw_hook, self.w_AVD_MBOX_INIT)
        self.hv.add_tracer(irange(self.base + 0x1098054, 4), "avd-mbox-54", TraceMode.SYNC, self.evt_rw_hook, self.w_AVD_MBOX_0054)
        self.hv.add_tracer(irange(self.base + 0x1098064, 4), "avd-mbox-64", TraceMode.SYNC, self.r_AVD_MBOX_0064, self.evt_rw_hook)

    def w_AVD_MBOX_INIT(self, val):
        if (int(val.value) == 0xe):
            self.state_active = True
            #self.hv.trace_range(irange(AVD_BASE + 0x1080000, 0x18000), mode=TraceMode.SYNC)
            #self.add_iova_tracer(stream=1, start=0x4000, size=0xb00)

    def poll(self):
        self.mon.poll()
        self.iomon.poll()
        self.iomon1.poll()

    def evt_rw_hook(self, x):
        self.poll()

    def w_AVD_MBOX_0054(self, x):
        if ((x.data >= 0x1080000) and (x.data <= 0x10a0000)):
            self.log("sent fw command at 0x%x" % (x.data))
            cmd = self.read_regs(self.base + x.data, 0x60)
            chexdump32(cmd)
            frame_params_iova = self.p.read32(self.base + x.data + 0x8)
            if (frame_params_iova != 0x0):
                t = datetime.datetime.now().isoformat()
                frame_params = self.dart.ioread(1, frame_params_iova, 0xb0000)
                outdir = os.path.join("data", self.outdir)
                os.makedirs(outdir, exist_ok=True)
                open(os.path.join(outdir, f'frame.{t}.{hex(frame_params_iova)}.bin'), "wb").write(frame_params)
                #open(os.path.join(outdir, f'idr.{t}.{hex(frame_params_iova)}.bin'), "wb").write(self.dart.ioread(0, 0x744000, 0x4000))
            self.poll()

    def r_AVD_MBOX_0064(self, x):
        if ((x.data >= 0x1080000) and (x.data <= 0x10a0000)):
            self.log("Received fw command at 0x%x" % (x.data))
            cmd = self.read_regs(self.base + x.data, 0x60)
            chexdump32(cmd)
            self.poll()

    def read_regs(self, addr, size):
        scratch = self.u.malloc(size)
        p.memcpy32(scratch, addr, size)
        return self.p.iface.readmem(scratch, size)

    def read_iova(self, start, end, stream=0):
            data = b''
            for i in range((end - start) // 0x4000):
                try:
                    d = self.dart_tracer.dart.ioread(stream, start + (i * 0x4000), 0x4000)
                except:
                    d = b'\0' * 0x4000
                data += d
            return data

p.pmgr_adt_clocks_enable('/arm-io/dart-avd')
p.pmgr_adt_clocks_enable('/arm-io/avd')
dart_tracer = DARTTracer(hv, "/arm-io/dart-avd", verbose=0)
dart_tracer.start()
dart = dart_tracer.dart

tracer = AVDTracer(hv, '/arm-io/avd', dart_tracer, verbose=3)
#tracer.start()

trace_device("/arm-io/avd", mode=TraceMode.SYNC)
trace_range(irange(AVD_BASE + 0x1080000, 0x18000), False)
