# SPDX-License-Identifier: MIT

# magic numbers everywhere...
# ironically solid though

class ANEPS:
    def __init__(self, ane):
        self.u = ane.u
        self.p = ane.p
        self.ps_base_addr = self.u.adt["arm-io/ane"].get_reg(1)[0]
        self.ps_regs = [self.ps_base_addr + 0xc000 + offset 
                                for offset in range(0x0, 0x38, 0x8)]

    def ps_pwrup_stage1(self):
        # last->first 
        for ps_reg in self.ps_regs[::-1]:
            self.p.write32(ps_reg, 0x300)
        return
    
    def ps_pwrup_stage2(self):
        # first->last 
        for ps_reg in self.ps_regs:
            self.p.write32(ps_reg, 0xf)
        return

    def pd_is_on(self, pd_value):
        return ((pd_value & 0xff) == 0xff)

    def read_ps_status(self):
        for pd_id, ps_reg in enumerate(self.ps_regs):
            pd_value = self.p.read32(ps_reg)
            print('pd %d: 0x%x, is_on: %r' 
                                % (pd_id, pd_value, self.pd_is_on(pd_value)))
        return

    def assert_ps_on(self):
        for pd_id, ps_reg in enumerate(self.ps_regs):
            pd_value = self.p.read32(ps_reg)
            if not (self.pd_is_on(pd_value)):
                raise ValueError('pd %d @ 0x%x is 0x%x' 
                                % (pd_id, ps_reg, pd_value))
        return


def powerup(ane):
    print('powering up ane...')
    ane.apply_static_pmgr_tunables()
    fill_pwr_initdata(ane)
    ane.apply_static_pmgr_tunables()
    # ---- ps ----
    ane_ps = ANEPS(ane)
    ane.apply_static_pmgr_tunables()
    ane_ps.ps_pwrup_stage1()
    apply_unk_pmgr_tunables(ane)
    ane.apply_static_pmgr_tunables()
    ane_ps.ps_pwrup_stage2()
    ane_ps.read_ps_status()
    ane_ps.assert_ps_on()
    # ---- ps ----
    ane.perf_regs.CTRL.val = 0xfff00000fff # on
    ane.apply_static_pmgr_tunables()
    pwr_reset_at_init(ane)
    ane.apply_static_pmgr_tunables()
    ane.perf_regs.CTRL.val = 0xfff00000fff # reset turns it off
    print('ane powered up!')
    return


def pwr_reset_at_init(ane):
    ane.regs.ASC_EDPRCR.val = 0x2
    ane.regs.PMGR1.val = 0xffff # re-apply tunables !!!
    ane.regs.PMGR2.val = 0xffff
    ane.regs.PMGR3.val = 0xffff
    # unk asc reset; stuff breaks otherwise
    ane.p.write32(ane.base_addr + 0x1400900, 0xffffffff)
    ane.p.write32(ane.base_addr + 0x1400904, 0xffffffff)
    ane.p.write32(ane.base_addr + 0x1400908, 0xffffffff)
    return


def apply_unk_pmgr_tunables(ane):
    p = ane.p
    p.read64(0x26a00c000)
    p.write32(0x26a008014, 0x1)
    p.read64(0x26a00c200)
    p.read64(0x26a00c230)
    p.read64(0x26a00c260)
    p.read64(0x26a00c290)
    p.read64(0x26a00c298)
    p.read64(0x26a00c2a0)
    p.read64(0x26a00c2a8)
    p.read64(0x26a00c2b0)
    p.read64(0x26a00c2b8)
    p.write32(0x26a0082bc, 0x1)
    p.read64(0x26a00c208)
    p.read64(0x26a00c238)
    p.read64(0x26a00c268)
    p.read64(0x26a00c2c0)
    p.read64(0x26a00c2c8)
    p.read64(0x26a00c2d0)
    p.read64(0x26a00c2d8)
    p.read64(0x26a00c2e0)
    p.read64(0x26a00c2e8)
    p.write32(0x26a0082bc, 0x2)
    p.read64(0x26a00c270)
    p.write32(0x26a0082bc, 0x4)
    return


def fill_pwr_initdata(ane):
    apply_more_pmgr_tunables(ane)

    fill_dpe_initdata(ane)
    fill_perf_initdata(ane)
    fill_dpe_ppt_soc_initdata(ane)

    # something perf 
    ane.p.write32(0x26b908000, 0x0)
    ane.p.write32(0x26b908000, 0x1)
    return 


def apply_more_pmgr_tunables(ane):
    p = ane.p
    p.write32(0x26a008000, 0x9)
    p.read32(0x26a000920)
    p.write32(0x26a000920, 0x80)
    p.write32(0x26a008008, 0x7)
    p.write32(0x26a008014, 0x1)
    p.read32(0x26a008018)
    p.write32(0x26a008018, 0x1)
    p.read32(0x26a000748)
    p.write32(0x26a000748, 0x1)
    p.write32(0x26a008208, 0x2)
    p.write32(0x26a008280, 0x20)
    p.write32(0x26a008288, 0x3)
    p.write32(0x26a00828c, 0xc)
    p.write32(0x26a008290, 0x18)
    p.write32(0x26a008294, 0x30)
    p.write32(0x26a008298, 0x78)
    p.write32(0x26a00829c, 0xff)
    p.read32(0x26a0082b8)
    p.write32(0x26a0082b8, 0x1)
    p.write32(0x26a0082bc, 0x1)
    p.read32(0x26a0082c0)
    p.write32(0x26a0082c0, 0x1)
    p.read32(0x26a000748)
    p.write32(0x26a000748, 0x1)
    p.write32(0x26a00820c, 0x3)
    p.write32(0x26a008284, 0x20)
    p.write32(0x26a0082a0, 0x3)
    p.write32(0x26a0082a4, 0xc)
    p.write32(0x26a0082a8, 0x18)
    p.write32(0x26a0082ac, 0x30)
    p.write32(0x26a0082b0, 0x78)
    p.write32(0x26a0082b4, 0xff)
    p.read32(0x26a0082b8)
    p.write32(0x26a0082b8, 0x3)
    p.write32(0x26a0082bc, 0x2)
    p.read32(0x26a0082c0)
    p.write32(0x26a0082c0, 0x3)
    p.write32(0x26a008210, 0x0)
    p.write32(0x26a008408, 0xd)
    p.write32(0x26a008418, 0x3)
    p.write32(0x26a00841c, 0x0)
    p.write32(0x26a008420, 0xffffffff)
    p.write32(0x26a008424, 0x0)
    p.write32(0x26a008428, 0xfff)
    p.read32(0x26a0082b8)
    p.write32(0x26a0082b8, 0x7)
    p.write32(0x26a0082bc, 0x4)
    p.read32(0x26a0082c0)
    p.write32(0x26a0082c0, 0x7)
    return 


def fill_dpe_initdata(ane):
    # presumably values are calcd from the read
    p = ane.p

    p.read32(0x26b8f003c)
    p.write32(0x26b8f003c, 0x262)
    p.read32(0x26b8f0040)
    p.write32(0x26b8f0040, 0x262)
    p.read32(0x26b8f0044)
    p.write32(0x26b8f0044, 0x2c8)
    p.read32(0x26b8f0048)
    p.write32(0x26b8f0048, 0x351)
    p.read32(0x26b8f004c)
    p.write32(0x26b8f004c, 0x391)
    p.read32(0x26b8f0050)
    p.write32(0x26b8f0050, 0x404)
    p.read32(0x26b8f0054)
    p.write32(0x26b8f0054, 0x441)
    p.read32(0x26b8f0058)
    p.write32(0x26b8f0058, 0x4b5)
    p.read32(0x26b8f005c)
    p.write32(0x26b8f005c, 0x4ec)
    p.read32(0x26b8f0060)
    p.write32(0x26b8f0060, 0x599)
    p.read32(0x26b8f0064)
    p.write32(0x26b8f0064, 0x647)
    p.read32(0x26b8f0068)
    p.write32(0x26b8f0068, 0x6f2)
    p.read32(0x26b8f006c)
    p.write32(0x26b8f006c, 0x82b)
    p.read32(0x26b8f0070)
    p.write32(0x26b8f0070, 0x82b)
    p.read32(0x26b8f0074)
    p.write32(0x26b8f0074, 0x82b)
    p.read32(0x26b8f0078)
    p.write32(0x26b8f0078, 0x82b)
    return 


def fill_perf_initdata(ane):
    # performance counters
    p = ane.p

    p.read32(0x26b908008)
    p.write32(0x26b908008, 0xf8a96)
    p.read32(0x26b90800c)
    p.write32(0x26b90800c, 0x11ca11)
    p.read32(0x26b908010)
    p.write32(0x26b908010, 0x15c4ad)
    p.read32(0x26b908014)
    p.write32(0x26b908014, 0x1cafc0)
    p.read32(0x26b908018)
    p.write32(0x26b908018, 0x1c858e)
    p.read32(0x26b90801c)
    p.write32(0x26b90801c, 0x20cf3d)
    p.read32(0x26b908020)
    p.write32(0x26b908020, 0x2087b1)
    p.read32(0x26b908024)
    p.write32(0x26b908024, 0x294c83)
    p.read32(0x26b908028)
    p.write32(0x26b908028, 0x2b6ffb)
    p.read32(0x26b90802c)
    p.write32(0x26b90802c, 0x2cfb4c)
    p.read32(0x26b908030)
    p.write32(0x26b908030, 0x305c9b)
    p.read32(0x26b908034)
    p.write32(0x26b908034, 0x2e277f)
    p.read32(0x26b908038)
    p.write32(0x26b908038, 0x0)
    p.read32(0x26b90803c)
    p.write32(0x26b90803c, 0x0)
    p.read32(0x26b908040)
    p.write32(0x26b908040, 0x0)
    p.read32(0x26b908048)
    p.write32(0x26b908048, 0xd47e2)
    p.read32(0x26b90804c)
    p.write32(0x26b90804c, 0x11ca11)
    p.read32(0x26b908050)
    p.write32(0x26b908050, 0x15c4ad)
    p.read32(0x26b908054)
    p.write32(0x26b908054, 0x1a1c07)
    p.read32(0x26b908058)
    p.write32(0x26b908058, 0x1c858e)
    p.read32(0x26b90805c)
    p.write32(0x26b90805c, 0x20cf3d)
    p.read32(0x26b908060)
    p.write32(0x26b908060, 0x2087b1)
    p.read32(0x26b908064)
    p.write32(0x26b908064, 0x270050)
    p.read32(0x26b908068)
    p.write32(0x26b908068, 0x28cacd)
    p.read32(0x26b90806c)
    p.write32(0x26b90806c, 0x2b19cc)
    p.read32(0x26b908070)
    p.write32(0x26b908070, 0x2b09f6)
    p.read32(0x26b908074)
    p.write32(0x26b908074, 0x2cd4e0)
    p.read32(0x26b908078)
    p.write32(0x26b908078, 0x0)
    p.read32(0x26b90807c)
    p.write32(0x26b90807c, 0x0)
    p.read32(0x26b908080)
    p.write32(0x26b908080, 0x0)
    p.read32(0x26b908088)
    p.write32(0x26b908088, 0xb8130)
    p.read32(0x26b90808c)
    p.write32(0x26b90808c, 0xf5f41)
    p.read32(0x26b908090)
    p.write32(0x26b908090, 0x12b938)
    p.read32(0x26b908094)
    p.write32(0x26b908094, 0x167287)
    p.read32(0x26b908098)
    p.write32(0x26b908098, 0x14710e)
    p.read32(0x26b90809c)
    p.write32(0x26b90809c, 0x18b58d)
    p.read32(0x26b9080a0)
    p.write32(0x26b9080a0, 0x147c37)
    p.read32(0x26b9080a4)
    p.write32(0x26b9080a4, 0x1635ee)
    p.read32(0x26b9080a8)
    p.write32(0x26b9080a8, 0x18560a)
    p.read32(0x26b9080ac)
    p.write32(0x26b9080ac, 0x18737e)
    p.read32(0x26b9080b0)
    p.write32(0x26b9080b0, 0x19e10d)
    p.read32(0x26b9080b4)
    p.write32(0x26b9080b4, 0x0)
    p.read32(0x26b9080b8)
    p.write32(0x26b9080b8, 0x0)
    p.read32(0x26b9080bc)
    p.write32(0x26b9080bc, 0x0)
    p.read32(0x26b9080c0)
    p.write32(0x26b9080c0, 0x0)
    return 


def fill_dpe_ppt_soc_initdata(ane):
    # aneDpePpt_soc_dpe_lee ? 
    p = ane.p

    p.read32(0x26b8f4024)
    p.write32(0x26b8f4024, 0x226)
    p.read32(0x26b8f4028)
    p.write32(0x26b8f4028, 0x6b7)
    p.read32(0x26b8f402c)
    p.write32(0x26b8f402c, 0xd8)
    p.read32(0x26b8f4030)
    p.write32(0x26b8f4030, 0x1af)
    p.read32(0x26b8f4034)
    p.write32(0x26b8f4034, 0x35e)
    p.read32(0x26b8f4038)
    p.write32(0x26b8f4038, 0x6bb)
    p.read32(0x26b8f403c)
    p.write32(0x26b8f403c, 0x226)
    p.read32(0x26b8f4040)
    p.write32(0x26b8f4040, 0x6b7)
    p.read32(0x26b8f4044)
    p.write32(0x26b8f4044, 0xd8)
    p.read32(0x26b8f4048)
    p.write32(0x26b8f4048, 0x1af)
    p.read32(0x26b8f404c)
    p.write32(0x26b8f404c, 0x35e)
    p.read32(0x26b8f4050)
    p.write32(0x26b8f4050, 0x6bb)
    p.read32(0x26b8f4054)
    p.write32(0x26b8f4054, 0x21c)
    p.read32(0x26b8f4058)
    p.write32(0x26b8f4058, 0x69a)
    p.read32(0x26b8f405c)
    p.write32(0x26b8f405c, 0xd4)
    p.read32(0x26b8f4060)
    p.write32(0x26b8f4060, 0x1a8)
    p.read32(0x26b8f4064)
    p.write32(0x26b8f4064, 0x34f)
    p.read32(0x26b8f4068)
    p.write32(0x26b8f4068, 0x69e)
    p.read32(0x26b8f406c)
    p.write32(0x26b8f406c, 0x213)
    p.read32(0x26b8f4070)
    p.write32(0x26b8f4070, 0x67c)
    p.read32(0x26b8f4074)
    p.write32(0x26b8f4074, 0xd0)
    p.read32(0x26b8f4078)
    p.write32(0x26b8f4078, 0x1a0)
    p.read32(0x26b8f407c)
    p.write32(0x26b8f407c, 0x340)
    p.read32(0x26b8f4080)
    p.write32(0x26b8f4080, 0x680)
    p.read32(0x26b8f4084)
    p.write32(0x26b8f4084, 0x210)
    p.read32(0x26b8f4088)
    p.write32(0x26b8f4088, 0x671)
    p.read32(0x26b8f408c)
    p.write32(0x26b8f408c, 0xcf)
    p.read32(0x26b8f4090)
    p.write32(0x26b8f4090, 0x19e)
    p.read32(0x26b8f4094)
    p.write32(0x26b8f4094, 0x33b)
    p.read32(0x26b8f4098)
    p.write32(0x26b8f4098, 0x675)
    p.read32(0x26b8f409c)
    p.write32(0x26b8f409c, 0x20b)
    p.read32(0x26b8f40a0)
    p.write32(0x26b8f40a0, 0x664)
    p.read32(0x26b8f40a4)
    p.write32(0x26b8f40a4, 0xcd)
    p.read32(0x26b8f40a8)
    p.write32(0x26b8f40a8, 0x19a)
    p.read32(0x26b8f40ac)
    p.write32(0x26b8f40ac, 0x334)
    p.read32(0x26b8f40b0)
    p.write32(0x26b8f40b0, 0x668)
    p.read32(0x26b8f40b4)
    p.write32(0x26b8f40b4, 0x20b)
    p.read32(0x26b8f40b8)
    p.write32(0x26b8f40b8, 0x662)
    p.read32(0x26b8f40bc)
    p.write32(0x26b8f40bc, 0xcd)
    p.read32(0x26b8f40c0)
    p.write32(0x26b8f40c0, 0x19a)
    p.read32(0x26b8f40c4)
    p.write32(0x26b8f40c4, 0x333)
    p.read32(0x26b8f40c8)
    p.write32(0x26b8f40c8, 0x666)
    p.read32(0x26b8f40cc)
    p.write32(0x26b8f40cc, 0x20e)
    p.read32(0x26b8f40d0)
    p.write32(0x26b8f40d0, 0x66d)
    p.read32(0x26b8f40d4)
    p.write32(0x26b8f40d4, 0xcf)
    p.read32(0x26b8f40d8)
    p.write32(0x26b8f40d8, 0x19d)
    p.read32(0x26b8f40dc)
    p.write32(0x26b8f40dc, 0x339)
    p.read32(0x26b8f40e0)
    p.write32(0x26b8f40e0, 0x671)
    p.read32(0x26b8f40e4)
    p.write32(0x26b8f40e4, 0x212)
    p.read32(0x26b8f40e8)
    p.write32(0x26b8f40e8, 0x67a)
    p.read32(0x26b8f40ec)
    p.write32(0x26b8f40ec, 0xd0)
    p.read32(0x26b8f40f0)
    p.write32(0x26b8f40f0, 0x1a0)
    p.read32(0x26b8f40f4)
    p.write32(0x26b8f40f4, 0x33f)
    p.read32(0x26b8f40f8)
    p.write32(0x26b8f40f8, 0x67e)
    p.read32(0x26b8f40fc)
    p.write32(0x26b8f40fc, 0x22d)
    p.read32(0x26b8f4100)
    p.write32(0x26b8f4100, 0x6cc)
    p.read32(0x26b8f4104)
    p.write32(0x26b8f4104, 0xda)
    p.read32(0x26b8f4108)
    p.write32(0x26b8f4108, 0x1b4)
    p.read32(0x26b8f410c)
    p.write32(0x26b8f410c, 0x368)
    p.read32(0x26b8f4110)
    p.write32(0x26b8f4110, 0x6d0)
    p.read32(0x26b8f4114)
    p.write32(0x26b8f4114, 0x25f)
    p.read32(0x26b8f4118)
    p.write32(0x26b8f4118, 0x768)
    p.read32(0x26b8f411c)
    p.write32(0x26b8f411c, 0xee)
    p.read32(0x26b8f4120)
    p.write32(0x26b8f4120, 0x1dc)
    p.read32(0x26b8f4124)
    p.write32(0x26b8f4124, 0x3b7)
    p.read32(0x26b8f4128)
    p.write32(0x26b8f4128, 0x76d)
    p.read32(0x26b8f412c)
    p.write32(0x26b8f412c, 0x2ab)
    p.read32(0x26b8f4130)
    p.write32(0x26b8f4130, 0x857)
    p.read32(0x26b8f4134)
    p.write32(0x26b8f4134, 0x10c)
    p.read32(0x26b8f4138)
    p.write32(0x26b8f4138, 0x217)
    p.read32(0x26b8f413c)
    p.write32(0x26b8f413c, 0x42e)
    p.read32(0x26b8f4140)
    p.write32(0x26b8f4140, 0x85c)
    p.read32(0x26b8f4144)
    p.write32(0x26b8f4144, 0x384)
    p.read32(0x26b8f4148)
    p.write32(0x26b8f4148, 0xafd)
    p.read32(0x26b8f414c)
    p.write32(0x26b8f414c, 0x161)
    p.read32(0x26b8f4150)
    p.write32(0x26b8f4150, 0x2c2)
    p.read32(0x26b8f4154)
    p.write32(0x26b8f4154, 0x583)
    p.read32(0x26b8f4158)
    p.write32(0x26b8f4158, 0xb05)
    p.read32(0x26b8f415c)
    p.write32(0x26b8f415c, 0x384)
    p.read32(0x26b8f4160)
    p.write32(0x26b8f4160, 0xafd)
    p.read32(0x26b8f4164)
    p.write32(0x26b8f4164, 0x161)
    p.read32(0x26b8f4168)
    p.write32(0x26b8f4168, 0x2c2)
    p.read32(0x26b8f416c)
    p.write32(0x26b8f416c, 0x583)
    p.read32(0x26b8f4170)
    p.write32(0x26b8f4170, 0xb05)
    p.read32(0x26b8f4174)
    p.write32(0x26b8f4174, 0x384)
    p.read32(0x26b8f4178)
    p.write32(0x26b8f4178, 0xafd)
    p.read32(0x26b8f417c)
    p.write32(0x26b8f417c, 0x161)
    p.read32(0x26b8f4180)
    p.write32(0x26b8f4180, 0x2c2)
    p.read32(0x26b8f4184)
    p.write32(0x26b8f4184, 0x583)
    p.read32(0x26b8f4188)
    p.write32(0x26b8f4188, 0xb05)
    p.read32(0x26b8f418c)
    p.write32(0x26b8f418c, 0x384)
    p.read32(0x26b8f4190)
    p.write32(0x26b8f4190, 0xafd)
    p.read32(0x26b8f4194)
    p.write32(0x26b8f4194, 0x161)
    p.read32(0x26b8f4198)
    p.write32(0x26b8f4198, 0x2c2)
    p.read32(0x26b8f419c)
    p.write32(0x26b8f419c, 0x583)
    p.read32(0x26b8f41a0)
    p.write32(0x26b8f41a0, 0xb05)
    return 
