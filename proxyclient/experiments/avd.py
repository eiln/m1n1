#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import sys, pathlib, argparse
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.append("/home/eileen/asahi/avd") # TODO it's for avdcgen

from m1n1.setup import *
from m1n1.utils import *
from m1n1.fw.avd import AVDDevice
from m1n1.fw.avd.decoder import AVDDecoder

from avdcgen.h264 import AvdH264Cgen
from avdcgen.h264.types import *

avd = AVDDevice(u)
avd.boot()
avd_r32 = avd.avd_r32; avd_w32 = avd.avd_w32; avd_r64 = avd.avd_r64; avd_w64 = avd.avd_w64
avd.poll()
avd.ioalloc_at(0x0, 0xd00000, stream=0)
avdec = AVDDecoder(avd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, default="x.h264")
    args = parser.parse_args()
    # ffmpeg -y -f lavfi -i testsrc=duration=30:size=128x64:rate=1,format=yuv420p -c:v libx264 x.h264
    # ffmpeg -y -t 9 -i ~/Downloads/matrixbench_mpeg2.mpg -s 128x64 -pix_fmt yuv420p -c:v libx264 x.h264
    cgen = AvdH264Cgen()
    cgen.stfu = True
    cgen.syn.stfu = True
    cgen.hal.stfu = True
    units = cgen.parse(args.input)
    for unit in units:
        inst = cgen.hal.generate(unit)
        avdec.decode(cgen.hal.ctx, unit, inst)
