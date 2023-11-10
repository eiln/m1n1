#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import sys, pathlib, argparse
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.append("/home/eileen/asahi/avd")

from m1n1.setup import *
from m1n1.utils import *
from m1n1.fw.avd import AVDDevice

from avd_emu import AVDEmulator
from avid.h264.decoder import AVDH264Decoder
from avid.vp9.decoder import AVDVP9Decoder

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-f','--firmware', type=str, required=True, help="path to CM3 firmware")
	parser.add_argument('-d','--dir', type=str, required=True, help="frame_params trace directory")
	parser.add_argument('-p','--prefix', type=str, default="data", help="directory prefix")
	args = parser.parse_args()

	paths = os.listdir(os.path.join(args.prefix, args.dir))
	paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "param" in path or "frame" in path])
	assert(len(paths))

	avd = AVDDevice(u)
	avdec = AVDDecoder(avd)
	avd.boot()
	avd.mcpu_decode_init(args.firmware)
	avd.poll()

	avd.ioalloc_at(0x0, 0xf00000, stream=0)
	avd.iomon.add(0x0, 0xf00000)
	avd.ioalloc_at(0x0, 0xb84000, stream=1)
	avd.iomon.poll()
	emu = AVDEmulator(args.firmware, stfu=True)
	emu.start()

	dec = AVDVP9Decoder()
	units = dec.parse(args.input)
	for n in range(len(units)):
		avd.decoder.set_payload(dec.ctx, units[i])
		cmd = emu.set_params(path)
		avd.iowrite(0x0, emu.dart1_space, stream=1)
		avd.iomon.poll()
		cmd_addr = 0x108eb90
		avd.avd_wbuf(cmd_addr, cmd)
		avd.avd_w32(0x1098054, cmd_addr)
		avd.poll()
		avd.iomon.poll()
