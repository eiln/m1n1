#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import sys, pathlib, argparse
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.append("/home/eileen/asahi/avd")

from m1n1.setup import *
from m1n1.utils import *
from m1n1.fw.avd import *
import cv2

from avd_emu import AVDEmulator
from avid.h264.decoder import AVDH264Decoder
from avid.vp9.decoder import AVDVP9Decoder
from avid.utils import *
from tools.common import *

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-f','--firmware', type=str, default="data/fw.bin", help="path to CM3 firmware")
	parser.add_argument('-i','--input', type=str, required=True, help="path to CM3 firmware")
	parser.add_argument('-d','--dir', type=str, required=True, help="frame_params trace directory")
	parser.add_argument('-p','--prefix', type=str, default="data", help="directory prefix")
	args = parser.parse_args()

	paths = os.listdir(os.path.join(args.prefix, args.dir))
	paths = sorted([os.path.join(args.prefix, args.dir, path) for path in paths if "frame" in path])
	assert(len(paths))

	avd = AVDDevice(u)
	avd.decoder = AVDVP9Dec(avd)
	avd.boot()
	avd.mcpu_decode_init(args.firmware)
	avd.poll()

	avd.ioalloc_at(0x0, 0xff0000, stream=0)
	#avd.iomon.add(0x0, 0xff0000)
	avd.ioalloc_at(0x0, 0xb84000, stream=1)
	avd.iomon.poll()
	emu = AVDEmulator(args.firmware, stfu=True)
	emu.start()

	dec = AVDVP9Decoder()
	dec.stfu = True
	dec.hal.stfu = True
	units = dec.setup(args.input, num=4, do_probs=True)
	for n in range(5):
		unit = units[n]
		inst = dec.decode(unit)
		avd.decoder.set_payload(dec.ctx, units[n])
		avd.decoder.avd.iowrite(dec.ctx.probs_addr, unit.get_probs(), stream=0)
		avd.iomon.poll()
		cmd = emu.set_params(paths[n])
		xxde(cmd)
		avd.iowrite(0x0, emu.dart1_space, stream=1)
		avd.iomon.poll()
		avd.avd_wbuf(emu.get_cmd_addr(n+1), cmd)
		avd.avd_w32(0x1098054, emu.get_cmd_addr(n+1))
		time.sleep(0.5)
		avd.poll()
		avd.iomon.poll()
		img = avd.decoder.get_nv12_disp_frame(dec.ctx)
		cv2.imshow(avd.decoder.winname, img); cv2.waitKey(100)
		open("data/x%d.bin" % n, "wb").write(avd.ioread(0x0, 0xff0000))
		break
