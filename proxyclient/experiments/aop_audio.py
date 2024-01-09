#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import struct
import traceback
from construct import *

from m1n1.setup import *
from m1n1.shell import run_shell
from m1n1.hw.dart import DART
from m1n1.fw.aop.client import AOPClient
from m1n1.fw.aop.ipc import *

# aop nodes have no clocks described in adt for j293. it does it itself
p.pmgr_adt_clocks_enable("/arm-io/aop")
p.pmgr_adt_clocks_enable("/arm-io/dart-aop")

# Set up a secondary proxy channel so that we can stream
# the microphone samples
p.usb_iodev_vuart_setup(p.iodev_whoami())
p.iodev_set_usage(IODEV.USB_VUART, USAGE.UARTPROXY)

pdm2 = u.adt["/arm-io/aop/iop-aop-nub/aop-audio/audio-pdm2"]
decm = u.adt["/arm-io/aop/iop-aop-nub/aop-audio/dc-2400000"]

pdm_config = Container(
    bytesPerSample=pdm2.bytesPerSample, # 2 ??
    clockSource=pdm2.clockSource, # 'pll '
    pdmFrequency=pdm2.pdmFrequency, # 2400000
    pdmcFrequency=pdm2.pdmcFrequency, # 24000000
    slowClockSpeed=pdm2.slowClockSpeed, # 24000000
    fastClockSpeed=pdm2.fastClockSpeed, # 24000000
    channelPolaritySelect=pdm2.channelPolaritySelect, # 256
    channelPhaseSelect=pdm2.channelPhaseSelect, # traces say 99 but device tree says 0
    unk8=0xf7600,
    unk9=0, # this should be latency (thus 15, see below) but traces say 0
    ratios=Container(
        r1=decm.ratios.r0,
        r2=decm.ratios.r1,
        r3=decm.ratios.r2,
    ),
    filterLengths=decm.filterLengths,
    coeff_bulk=120,
    coefficients=GreedyRange(Int32sl).parse(decm.coefficients),
    unk10=1,
    micTurnOnTimeMs=pdm2.micTurnOnTimeMs, # 20
    unk11=1,
    micSettleTimeMs=pdm2.micSettleTimeMs, # 50
)

decimator_config = Container(
    latency=decm.latency, # 15
    ratios=Container(
        r1=decm.ratios.r0, # 15
        r2=decm.ratios.r1, # 5
        r3=decm.ratios.r2, # 2
    ),
    filterLengths=decm.filterLengths,
    coeff_bulk=120,
    coefficients=GreedyRange(Int32sl).parse(decm.coefficients),
)

dart = DART.from_adt(u, "/arm-io/dart-aop",
                     iova_range=(u.adt["/arm-io/dart-aop"].vm_base, 0x1000000000))
dart.initialize()

aop = AOPClient(u, "/arm-io/aop", dart)
aop.update_bootargs({
    'p0CE': 0x20000,
    'laCn': 0x0,
    'tPOA': 0x1,
    "gila": 0x80,
})
aop.verbose = 4

p.dapf_init_all()
aop.asc.OUTBOX_CTRL.val = 0x20001 # (FIFOCNT=0x0, OVERFLOW=0, EMPTY=1, FULL=0, RPTR=0x0, WPTR=0x0, ENABLE=1)

# incredible power state naming scheme:
# idle: in sleep state (default at boot)
# pw1 : in active state (admac powers on) but not capturing
# pwrd: start capturing
# to start capturing, we put the 'hpai' (high power audio input?) device
# from idle -> pw1 -> pwrd state. it starts capturing at pwrd
# shutdown sequence must also be pwrd -> pw1 -> idle

def aop_start():
    aop.audio.indirect(SetDeviceProp(
        devid=u'hpai',
        modifier=202,
        data=Container(
            devid=u'hpai',
            cookie=2,
            target_pstate=u'pwrd',
            unk2=1,
        )
    )).check_retcode()

def aop_stop():
    aop.audio.indirect(SetDeviceProp(
        devid='hpai',
        modifier=202,
        data=Container(
            devid='hpai',
            cookie=3,
            target_pstate='pw1 ',
            unk2=1,
        )
    )).check_retcode()

    aop.audio.indirect(SetDeviceProp(
        devid='hpai',
        modifier=202,
        data=Container(
            devid='hpai',
            cookie=4,
            target_pstate='idle',
            unk2=0,
        )
    )).check_retcode()

def main():
    aop.start()
    for epno in [0x20, 0x21, 0x22, 0x24, 0x25, 0x26, 0x27, 0x28]:
        aop.start_ep(epno)
    timeout = 5
    while (not aop.audio.ready) and timeout:
        aop.work_for(0.1)
        timeout -= 1
    if not timeout:
        raise Exception("Timed out waiting on audio endpoint")
    print("Finished boot")
    audep = aop.audio

    audep.roundtrip(AttachDevice(devid='pdm0')).check_retcode() # leap signal processor and etc; leap is low-energy audio processor I think
    audep.roundtrip(AttachDevice(devid='hpai')).check_retcode() # high power audio input? actual mic
    audep.roundtrip(AttachDevice(devid='lpai')).check_retcode() # low power audio input? seems to be voice trigger mic
    audep.roundtrip(SetDeviceProp(
        devid='lpai', modifier=301, data=Container(unk1=7, unk2=7, unk3=1, unk4=7))
    ).check_retcode()
    audep.indirect(SetDeviceProp(
        devid='pdm0', modifier=200, data=pdm_config)
    ).check_retcode()
    audep.indirect(SetDeviceProp(
        devid='pdm0', modifier=210, data=decimator_config)
    ).check_retcode()

    dump = """
00000000  08 00 00 10 00 00 00 00  02 2d 00 00 00 00 00 00  |.........-......|
00000010  00 00 00 00 00 00 00 00  34 00 00 00 02 10 20 00  |........4..... .|
00000020  2d 00 00 00 00 00 00 00  00 00 00 00 08 00 00 00  |-...............|
00000030  00 00 00 00 ff ff ff ff  04 00 00 c3 00 00 00 00  |................|
00000040  00 00 00 00 00 00 00 00  00 00 00 00 a0 61 70 68  |.............aph|
00000050  30 00 00 00 00 00 00 00  69 61 70 68 c8 00 00 00  |0.......iaph....|
00000060  01 00 00 00                                       |....            |
"""
    audep.send_ipc(chexundump(dump)) # optional hello. gets "idle" for response
    aop.work_for(0.1)

    audep.indirect(SetDeviceProp(
        devid='hpai',
        modifier=202,
        data=Container(
            devid='hpai',
            cookie=1,
            target_pstate='pw1 ',
            unk2=0,
        )
    )).check_retcode()

try:
    main()
    pass
except KeyboardInterrupt:
    pass
except Exception:
    print(traceback.format_exc())

run_shell(locals(), poll_func=aop.work)
