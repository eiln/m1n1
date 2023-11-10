# SPDX-License-Identifier: MIT
import cv2
import numpy as np
import time

class AVDFrame:
    def __init__(self, img, sl):
        self.img = img
        self.sl = sl

class AVDDecoder:
    def __init__(self, avd):
        self.avd = avd
        self.frames = []
        self.last_poc = -1
        self.winname = "img"

    def log(self, x):
        return self.avd.log(x)

    def get_nv12_disp_frame(self, ctx):
        y_data = self.avd.ioread(ctx.y_addr, ctx.width * ctx.height, stream=0)
        y = np.frombuffer(y_data, dtype=np.uint8).reshape((ctx.height, ctx.width))
        uv_data = self.avd.ioread(ctx.uv_addr, ctx.width * (ctx.height // 2), stream=0)
        uv = np.frombuffer(uv_data, dtype=np.uint8).reshape((ctx.height // 2, ctx.width))
        #u2 = np.repeat(np.repeat(uv[::,::2], repeats=2, axis=0), repeats=2, axis=1)
        u2 = cv2.resize(uv[:,::2], (ctx.width, ctx.height), interpolation=cv2.INTER_AREA)
        #v2 = np.repeat(np.repeat(uv[:,1::2], repeats=2, axis=0), repeats=2, axis=1)
        v2 = cv2.resize(uv[:,1::2], (ctx.width, ctx.height), interpolation=cv2.INTER_AREA)
        yuv = np.stack((y, u2, v2), axis=-1)
        return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

    def get_nv12_disp_frame2(self, ctx):
        y_data = self.avd.ioread(0x768100, ctx.width * ctx.height, stream=0)
        y = np.frombuffer(y_data, dtype=np.uint8).reshape((ctx.height, ctx.width))
        uv_data = self.avd.ioread(0x76c900, ctx.width * (ctx.height // 2), stream=0)
        uv = np.frombuffer(uv_data, dtype=np.uint8).reshape((ctx.height // 2, ctx.width))
        #u2 = np.repeat(np.repeat(uv[::,::2], repeats=2, axis=0), repeats=2, axis=1)
        u2 = cv2.resize(uv[:,::2], (ctx.width, ctx.height), interpolation=cv2.INTER_AREA)
        #v2 = np.repeat(np.repeat(uv[:,1::2], repeats=2, axis=0), repeats=2, axis=1)
        v2 = cv2.resize(uv[:,1::2], (ctx.width, ctx.height), interpolation=cv2.INTER_AREA)
        yuv = np.stack((y, u2, v2), axis=-1)
        return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

    def set_insn(self, x, sl):
        if (sl.mode == "h264"):
            self.avd.avd_w32(0x110400c, x.val)
        elif (sl.mode == "vp09"):
            self.avd.avd_w32(0x1104010, x.val)

    def set_payload(self, ctx, sl):
        self.avd.iowrite(ctx.slice_data_addr, sl.get_payload(), stream=0)
        if (sl.mode == "vp09"):
            self.avd.iowrite(ctx.probs_addr, sl.get_probs(), stream=0)
        self.avd.iomon.poll()

    def setup_dma(self, ctx, sl):
        avd_w32 = self.avd.avd_w32; avd_r32 = self.avd.avd_r32
        #self.avd.avd_dma_tunables_stage0()
        assert((ctx.inst_fifo_idx >= 0) and (ctx.inst_fifo_idx < ctx.inst_fifo_count))
        avd_w32(0x1104068 + (ctx.inst_fifo_idx * 0x4), ctx.inst_fifo_iova >> 8)
        avd_w32(0x1104084 + (ctx.inst_fifo_idx * 0x4), 0x100000)
        avd_w32(0x11040a0 + (ctx.inst_fifo_idx * 0x4), 0x0)
        avd_w32(0x11040bc + (ctx.inst_fifo_idx * 0x4), 0x0)
        if (sl.mode == "h264"):
            avd_w32(0x1104048, 0x0)
        elif (sl.mode == "vp09"):
            avd_w32(0x110404c, 0x0)

        if (sl.mode == "h264"):
            x = 0x1c00
        elif (sl.mode == "vp09"):
            x = 0x38000
        else:
            x = 0x1c00
        avd_w32(0x110405c, avd_r32(0x110405c) | x)
        self.avd.poll()

    def get_disp_frame(self, ctx, sl):
        avd_w32 = self.avd.avd_w32; avd_r32 = self.avd.avd_r32

        base = 0x2b000100
        if (sl.mode == "vp09"):
            base = 0x2bfff100
        avd_w32(0x1104014, base + (ctx.inst_fifo_idx * 0x10) | 7)
        for n in range(100):
            status = avd_r32(0x1104060)
            if (status & 0xc00000 == 0xc00000): # 0x2843108 -> 0x2c43108
                break
            self.log("status: 0x%x" % (status))
        avd_w32(0x1104060, 0x1000)
        for n in range(100):
            status = avd_r32(0x1104060)
            if (status & 0x3000 == 0x2000): # 0x2843108 -> 0x2c42108
                break
            self.log("status: 0x%x" % (status))
        avd_w32(0x1104060, 0x400000)
        self.avd.poll(); self.avd.iomon.poll()

    def display(self, frame):
        cv2.imshow(self.winname, frame.img); cv2.waitKey(1)
        if (frame.sl.mode == "h264"):
            self.last_poc = frame.sl.pic.poc
        else:
            self.last_poc = 0
        self.frames = [f for f in self.frames if f != frame]

    def decode(self, ctx, sl, inst_stream):
        if not inst_stream: return
        self.set_payload(ctx, sl)
        self.setup_dma(ctx, sl)
        for x in inst_stream:
            self.set_insn(x, sl)
        self.avd.poll(); self.avd.iomon.poll()
        self.get_disp_frame(ctx, sl)
        if (sl.mode == "vp09"):
            img = self.get_nv12_disp_frame2(ctx)
        else:
            img = self.get_nv12_disp_frame(ctx)
        self.frames.append(AVDFrame(img, sl))

        if (sl.mode == "h264"):
            dpb_size = ctx.sps_list[0].num_reorder_frames + 1
            if (len(self.frames) >= dpb_size):
                    frames = [f for f in self.frames if f.sl.pic.poc == self.last_poc + 2]
                    if (len(frames) == 1):
                        self.display(frames[0])
                        return
                    frames = sorted(self.frames, key=lambda f: (f.sl.pic.poc))
                    self.display(frames[0])
        elif (sl.mode == "vp09"):
            self.display(self.frames[0])
