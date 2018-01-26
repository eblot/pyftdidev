from array import array
from ftdi_spi import get_port
from time import sleep


class EPD:

    # Display resolution
    EPD_WIDTH = 128
    EPD_HEIGHT = 296

    # EPD2IN9 commands
    DRIVER_OUTPUT_CONTROL = 0x01
    BOOSTER_SOFT_START_CONTROL = 0x0C
    GATE_SCAN_START_POSITION = 0x0F
    DEEP_SLEEP_MODE = 0x10
    DATA_ENTRY_MODE_SETTING = 0x11
    SW_RESET = 0x12
    TEMPERATURE_SENSOR_CONTROL = 0x1A
    MASTER_ACTIVATION = 0x20
    DISPLAY_UPDATE_CONTROL_1 = 0x21
    DISPLAY_UPDATE_CONTROL_2 = 0x22
    WRITE_RAM = 0x24
    WRITE_VCOM_REGISTER = 0x2C
    WRITE_LUT_REGISTER = 0x32
    SET_DUMMY_LINE_PERIOD = 0x3A
    SET_GATE_TIME = 0x3B
    BORDER_WAVEFORM_CONTROL = 0x3C
    SET_RAM_X_ADDRESS_START_END_POSITION = 0x44
    SET_RAM_Y_ADDRESS_START_END_POSITION = 0x45
    SET_RAM_X_ADDRESS_COUNTER = 0x4E
    SET_RAM_Y_ADDRESS_COUNTER = 0x4F
    TERMINATE_FRAME_READ_WRITE = 0xFF

    LUT_FULL_UPDATE = (
        0x02, 0x02, 0x01, 0x11, 0x12, 0x12, 0x22, 0x22, 0x66, 0x69, 0x69, 0x59,
        0x58, 0x99, 0x99, 0x88, 0x00, 0x00, 0x00, 0x00, 0xF8, 0xB4, 0x13, 0x51,
        0x35, 0x51, 0x51, 0x19, 0x01, 0x00
    )

    LUT_PARTIAL_UPDATE = (
        0x10, 0x18, 0x18, 0x08, 0x18, 0x18, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x13, 0x14, 0x44, 0x12,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    )

    def __init__(self):
        self.width = self.EPD_WIDTH
        self.height = self.EPD_HEIGHT
        self.lut = self.LUT_FULL_UPDATE
        self.port = get_port()

    def delay_ms(self, delaytime):
        sleep(delaytime / 1000.0)

    def send_command(self, command):
        self.port.write_command(command)

    def send_data(self, data):
        self.port.write_data(data)

    def init(self, lut):
        if not self.port:
            raise IOError('No port')
        self.port.open()
        # EPD hardware init start
        self.lut = lut
        self.reset()
        self.send_command(self.DRIVER_OUTPUT_CONTROL)
        self.send_data((self.EPD_HEIGHT - 1) & 0xFF)
        self.send_data(((self.EPD_HEIGHT - 1) >> 8) & 0xFF)
        self.send_data(0x00)                     # GD = 0 SM = 0 TB = 0
        self.send_command(self.BOOSTER_SOFT_START_CONTROL)
        self.send_data(0xD7)
        self.send_data(0xD6)
        self.send_data(0x9D)
        self.send_command(self.WRITE_VCOM_REGISTER)
        self.send_data(0xA8)                     # VCOM 7C
        self.send_command(self.SET_DUMMY_LINE_PERIOD)
        self.send_data(0x1A)                     # 4 dummy lines per gate
        self.send_command(self.SET_GATE_TIME)
        self.send_data(0x08)                     # 2us per line
        self.send_command(self.DATA_ENTRY_MODE_SETTING)
        self.send_data(0x03)                     # X increment Y increment
        self.set_lut(self.lut)
        # EPD hardware init end

    def fini(self):
        self.port.close()

    def wait_until_idle(self):
        self.port.wait_ready()

    def reset(self):
        self.port.reset()

    def set_lut(self, lut):
        """set the look-up table register"""
        self.lut = lut
        self.send_command(self.WRITE_LUT_REGISTER)
        # the length of look-up table is 30 bytes
        for i in range(0, len(lut)):
            self.send_data(self.lut[i])

    def get_frame_buffer(self, image):
        """convert an image to a buffer"""
        buf = [0x00] * (self.width * self.height / 8)
        # Set buffer to value of Python Imaging Library image.
        # Image must be in mode 1.
        image_monocolor = image.convert('1')
        imwidth, imheight = image_monocolor.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError('Image must be same dimensions as display \
                ({0}x{1}).' .format(self.width, self.height))

        pixels = image_monocolor.load()
        for y in range(self.height):
            for x in range(self.width):
                # Set the bits for the column of pixels at the current
                # position.
                if pixels[x, y] != 0:
                    buf[(x + y * self.width) / 8] |= 0x80 >> (x % 8)
        return buf

    def set_frame_memory(self, image, x, y):
        """put an image to the frame memory.
           this won't update the display.
        """
        if (image is None or x < 0 or y < 0):
            return
        image_monocolor = image.convert('1')
        image_width, image_height = image_monocolor.size
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        x = x & 0xF8
        image_width = image_width & 0xF8
        if (x + image_width >= self.width):
            x_end = self.width - 1
        else:
            x_end = x + image_width - 1
        if (y + image_height >= self.height):
            y_end = self.height - 1
        else:
            y_end = y + image_height - 1
        self.set_memory_area(x, y, x_end, y_end)
        self.set_memory_pointer(x, y)
        self.send_command(self.WRITE_RAM)
        # send the image data
        pixels = image_monocolor.load()
        byte_to_send = 0x00
        buf = array('B')
        for j in range(0, y_end - y + 1):
            # 1 byte = 8 pixels, steps of i = 8
            for i in range(0, x_end - x + 1):
                # Set the bits for the column of pixels at the current
                # position.
                if pixels[i, j] != 0:
                    byte_to_send |= 0x80 >> (i % 8)
                if (i % 8 == 7):
                    buf.append(byte_to_send)
                    byte_to_send = 0x00
        self.send_data(buf)

    def clear_frame_memory(self, color):
        """clear the frame memory with the specified color.
           this won't update the display.
        """
        self.set_memory_area(0, 0, self.width - 1, self.height - 1)
        self.set_memory_pointer(0, 0)
        self.send_command(self.WRITE_RAM)
        # send the color data
        for i in range(0, self.width // 8 * self.height):
            self.send_data(color)

    def display_frame(self):
        """update the display
           there are 2 memory areas embedded in the e-paper display
           but once this function is called,
           the the next action of SetFrameMemory or ClearFrame will
           set the other memory area.
        """
        self.send_command(self.DISPLAY_UPDATE_CONTROL_2)
        self.send_data(0xC4)
        self.send_command(self.MASTER_ACTIVATION)
        self.send_command(self.TERMINATE_FRAME_READ_WRITE)
        self.wait_until_idle()

    def set_memory_area(self, x_start, y_start, x_end, y_end):
        """specify the memory area for data R/W"""
        self.send_command(self.SET_RAM_X_ADDRESS_START_END_POSITION)
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self.send_data(array('B', [(x_start >> 3) & 0xFF,
                                   (x_end >> 3) & 0xFF]))
        self.send_command(self.SET_RAM_Y_ADDRESS_START_END_POSITION)
        self.send_data(array('B', [y_start & 0xFF,
                                   (y_start >> 8) & 0xFF,
                                   y_end & 0xFF,
                                   (y_end >> 8) & 0xFF]))

    def set_memory_pointer(self, x, y):
        """specify the start point for data R/W"""
        self.send_command(self.SET_RAM_X_ADDRESS_COUNTER)
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self.send_data((x >> 3) & 0xFF)
        self.send_command(self.SET_RAM_Y_ADDRESS_COUNTER)
        self.send_data(array('B', [y & 0xFF, (y >> 8) & 0xFF]))
        self.wait_until_idle()

    def sleep(self):
        """After this command is transmitted, the chip would enter the
           deep-sleep mode to save power.
           The deep sleep mode would return to standby by hardware reset.
           You can use reset() to awaken or init() to initialize
        """
        self.send_command(self.DEEP_SLEEP_MODE)
        self.wait_until_idle()
