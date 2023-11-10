#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import sys, pathlib, argparse
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.append("/home/eileen/asahi/avd")

from m1n1.setup import *
from m1n1.utils import *
from m1n1.fw.avd import AVDDevice

from avid.vp9.decoder import AVDVP9Decoder

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, required=True)
    args = parser.parse_args()
    dec = AVDVP9Decoder()
    dec.stfu = True
    dec.hal.stfu = True
    units = dec.setup(args.input)

    avd = AVDDevice(u)
    avd.stfu = True
    avd.boot()
    avd.ioalloc_at(0x0, 0xf00000, stream=0)
    avd.iomon.add(0x0, 0xf00000)
    avd.iomon.poll()

    avd.decoder.winname = args.input
    for i,unit in enumerate(units[:]):
        inst = dec.decode(unit)
        avd.decoder.decode(dec.ctx, unit, inst)
