# SPDX-License-Identifier: MIT
import cv2
import numpy as np

class AVDDecoder:
    def __init__(self, avd):
        self.avd = avd

    def get_nv12_disp_frame(self, ctx):
        y_data = self.avd.ioread(ctx.y_iova, ctx.width * ctx.height, stream=0)
        y = np.frombuffer(y_data, dtype=np.uint8).reshape((ctx.height, ctx.width))
        uv_data = self.avd.ioread(ctx.uv_iova, ctx.width * (ctx.height // 2), stream=0)
        uv = np.frombuffer(uv_data, dtype=np.uint8).reshape((ctx.height // 2, ctx.width))
        u2 = np.repeat(np.repeat(uv[::,::2], repeats=2, axis=0), repeats=2, axis=1)
        v2 = np.repeat(np.repeat(uv[:,1::2], repeats=2, axis=0), repeats=2, axis=1)
        yuv = np.stack((y, u2, v2), axis=-1)
        return cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)

    def set_insn(self, x):
        self.avd.avd_w32(0x110400c, x)

    def set_payload(self, ctx, nalu):
        payload = nalu.get_payload()
        self.avd.iowrite(ctx.slice_iova, payload, stream=0)
        self.avd.iomon.poll()

    def setup_dma(self, ctx):
        avd_w32 = self.avd.avd_w32; avd_r32 = self.avd.avd_r32
        #avd.avd_dma_tunables_stage0()
        assert((ctx.slot >= 0) and (ctx.slot < 6))
        avd_w32(0x1104068 + (ctx.slot * 0x4), ctx.bounce_iova >> 8)
        avd_w32(0x1104084 + (ctx.slot * 0x4), 0x100000)
        avd_w32(0x11040a0 + (ctx.slot * 0x4), 0x0)
        avd_w32(0x11040bc + (ctx.slot * 0x4), 0x0)
        avd_w32(0x1104048, 0x0)
        avd_w32(0x110405c, avd_r32(0x110405c) | 0x1c00)
        self.avd.poll()

    def get_disp_frame(self, ctx, nalu):
        avd_w32 = self.avd.avd_w32; avd_r32 = self.avd.avd_r32
        avd_w32(0x1104014, 0x2b000107 + (ctx.slot * 0x10))
        avd_w32(0x1104060, 0x1000)
        avd_w32(0x1104060, 0x400000)
        self.avd.poll(); self.avd.iomon.poll()

    def decode(self, ctx, nalu, insn):
        if not insn: return
        self.set_payload(ctx, nalu)
        self.setup_dma(ctx)
        for x in insn:
            self.set_insn(x)
        self.get_disp_frame(ctx, nalu)
        img = self.get_nv12_disp_frame(ctx)
        cv2.imshow("img", img); cv2.waitKey(10)
