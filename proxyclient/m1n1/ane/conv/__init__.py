
def input_size_T(input_size):
    td_magic = [
        0x2000000, 0x0, 0x422, 0x0, 0xfff86a, 0x0, 0x30009800, 0x0,
        0x1024025, 0x21, 0xf401f800, 0x40, 0x0, 0x81, 0x80, 0x80,
        0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80,
        0x80, 0x80, 0x80, 0x80, 0x80, 0x0, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x40, 0x40, 0x40,
        0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x40, 0x40,
        0x40, 0x40, 0x40, 0x40, 0x40, 0x80, 0x80, 0x80,
        0x80, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x3c000000, 0x10001, 0x1, 0x22, 0x4, 0x1, 0x10001,
        0x1, 0x5000a021, 0x2041, 0x10001, 0x1, 0x0, 0x0, 0x4044405,
        0x100000, 0x0, 0x6c013800, 0x33881, 0x8880, 0x0, 0x40, 0x40,
        0x100, 0x100, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x1002031, 0x0, 0x100, 0x0, 0x0, 0x0, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x44004800,
        0x0, 0x500172, 0x0, 0x10, 0x40, 0x40, 0x40, 0x0,
        0x0, 0x0, 0x0, 0x0, 0x500172, 0x40, 0x10, 0x20,
        0x10, 0x10, 0xc008800, 0x0, 0x0, 0x0, 0x0, 0x1000c800,
        0x82, 0x101c00, 0x0, 0x0, 0x3c00, 0x18017800, 0xc1, 0x0,
        0x40, 0x40, 0x40, 0x40, 0x1302031
    ]

    batch = ((input_size-1)//8)

    td_magic[0x4//4] = int(input_size >= 0x36)
    
    td_magic[0x128//4] = 0x10001 * input_size
    td_magic[0x13c//4] = 0x10001 * input_size
    td_magic[0x150//4] = input_size

    if (batch == 0):
        td_magic[0x15c//4] = 0x4044405
    if (batch == 1):
        td_magic[0x15c//4] = 0x4031101
    if (batch == 2):
        td_magic[0x15c//4] = 0x4041101
    if (batch == 3):
        td_magic[0x15c//4] = 0x4021101
    if (batch == 4):
        td_magic[0x15c//4] = 0x4041101 
    if (batch == 5):
        td_magic[0x15c//4] = 0x4031101
    if (batch == 6):
        td_magic[0x15c//4] = 0x4041101
    if (batch == 7):
        td_magic[0x15c//4] = 0x4011101

    td_magic[0x17c//4] = input_size * 0x40
    td_magic[0x180//4] = 0x100 * input_size
    td_magic[0x184//4] = 0x100 * input_size
    
    td_magic[0x178//4] *= (batch // 4) + 1
    td_magic[0x17c//4] *= (batch // 4) + 1
    td_magic[0x180//4] *= (batch // 4) + 1
    td_magic[0x184//4] *= (batch // 4) + 1

    td_magic[0x1ec//4] = (batch + 1) * 0x10
    td_magic[0x1f0//4] = (batch + 1) * 0x40
    td_magic[0x1f4//4] = (batch + 1) * 0x40
    td_magic[0x1f8//4] = (batch + 1) * 0x40
    
    td_magic[0x214//4] = input_size * 0x40 * (batch + 1)
    if (batch not in [3,7]):
        td_magic[0x218//4] = batch * 0x10 + 0x10
        if (batch in [2,4,5,6]):
            td_magic[0x21c//4] = batch * 0x10 + 0x10
        td_magic[0x220//4] = batch * 0x10 + 0x10
        td_magic[0x224//4] = batch * 0x10 + 0x10
    else:
        td_magic[0x210//4] = 0x50017a
        td_magic[0x218//4] = 0x0
        td_magic[0x21c//4] = 0x0
        td_magic[0x220//4] = 0x0
        td_magic[0x224//4] = 0x0
        td_magic[0x258//4] |= 0x4000000
    
    td_magic[0x264//4] = input_size * 0x40
    td_magic[0x268//4] = input_size * 0x40
    td_magic[0x26c//4] = input_size * 0x40
    
    td_magic[0x260//4] *= (batch // 4) + 1
    td_magic[0x264//4] *= (batch // 4) + 1
    td_magic[0x268//4] *= (batch // 4) + 1
    td_magic[0x26c//4] *= (batch // 4) + 1

    return td_magic


def transform(input_size):
    return input_size_T(input_size)


def get_conv_dims(
            filters=1, kernel_size=1, stride=1, 
            dilation_rate=1, padding='valid',
            batch_size=1, input_channels=4, input_size=8,
            ):

    input_dim = (batch_size, input_channels, input_size, input_size)
    weight_dim = (filters, input_channels, kernel_size, kernel_size)

    kernel_size_dilated = (kernel_size - 1) * dilation_rate + 1
    out_spatial_size = (input_size - kernel_size_dilated) // stride + 1
    output_dim = (batch_size, filters, out_spatial_size, out_spatial_size)
    return input_dim, weight_dim, output_dim
