"""liquidctl drivers for fourth-generation NZXT Kraken X and Z liquid coolers.

Supported devices:

- NZXT Kraken X (X53, X63 and Z73)
- NZXT Kraken Z (Z53, Z63 and Z73)

Copyright (C) 2020–2022  Tom Frey, Jonas Malaco, Shady Nawara and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""
# uses the psf/black style

import itertools
import io
import math
import logging

try:
    # The hidapi package, depending on how it's compiled, exposes one or two
    # top level modules: hid and, optionally, hidraw.  When both are available,
    # hid will be a libusb-based fallback implementation, and we prefer hidraw.
    import hidraw as hid
except ModuleNotFoundError:
    import hid


from PIL import Image, ImageSequence

from liquidctl.error import NotSupportedByDevice
from liquidctl.driver.usb import UsbDriver, HidapiDevice
from liquidctl.util import (
    normalize_profile,
    interpolate_profile,
    clamp,
    Hue2Accessory,
    HUE2_MAX_ACCESSORIES_IN_CHANNEL,
    map_direction,
)

_LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_BULK_WRITE_LENGTH = 512
_MAX_READ_ATTEMPTS = 12

_STATUS_TEMPERATURE = "Liquid temperature"
_STATUS_PUMP_SPEED = "Pump speed"
_STATUS_PUMP_DUTY = "Pump duty"
_STATUS_FAN_SPEED = "Fan speed"
_STATUS_FAN_DUTY = "Fan duty"

# Available speed channels for model Z coolers
# name -> (channel_id, min_duty, max_duty)
# TODO adjust min duty values to what the firmware enforces
_SPEED_CHANNELS_KRAKENZ = {
    "pump": (0x1, 20, 100),
    "fan": (0x2, 0, 100),
}

_CRITICAL_TEMPERATURE = 59

# Available color channels and IDs for model Z coolers
_COLOR_CHANNELS_KRAKENZ = {
    "external": 0b001,
}

# Available LED channel modes/animations
# name -> (mode, size/variant, speed scale, min colors, max colors)
# FIXME any point in a one-color *alternating* or tai-chi animations?
# FIXME are all modes really supported by all channels? (this is better because
#       of synchronization, but it's not how the previous generation worked, so
#       I would like to double check)
_COLOR_MODES = {
    "off": (0x00, 0x00, 0, 0, 0),
    "fixed": (0x00, 0x00, 0, 1, 1),
    "fading": (0x01, 0x00, 1, 1, 8),
    "super-fixed": (0x01, 0x01, 9, 1, 40),
    "spectrum-wave": (0x02, 0x00, 2, 0, 0),
    "marquee-3": (0x03, 0x03, 2, 1, 1),
    "marquee-4": (0x03, 0x04, 2, 1, 1),
    "marquee-5": (0x03, 0x05, 2, 1, 1),
    "marquee-6": (0x03, 0x06, 2, 1, 1),
    "covering-marquee": (0x04, 0x00, 2, 1, 8),
    "alternating-3": (0x05, 0x03, 3, 1, 2),
    "alternating-4": (0x05, 0x04, 3, 1, 2),
    "alternating-5": (0x05, 0x05, 3, 1, 2),
    "alternating-6": (0x05, 0x06, 3, 1, 2),
    "moving-alternating-3": (0x05, 0x03, 4, 1, 2),
    "moving-alternating-4": (0x05, 0x04, 4, 1, 2),
    "moving-alternating-5": (0x05, 0x05, 4, 1, 2),
    "moving-alternating-6": (0x05, 0x06, 4, 1, 2),
    "pulse": (0x06, 0x00, 5, 1, 8),
    "breathing": (0x07, 0x00, 6, 1, 8),
    "super-breathing": (0x03, 0x00, 10, 1, 40),
    "candle": (0x08, 0x00, 0, 1, 1),
    "starry-night": (0x09, 0x00, 5, 1, 1),
    "rainbow-flow": (0x0B, 0x00, 2, 0, 0),
    "super-rainbow": (0x0C, 0x00, 2, 0, 0),
    "rainbow-pulse": (0x0D, 0x00, 2, 0, 0),
    "loading": (0x10, 0x00, 8, 1, 1),
    "tai-chi": (0x0E, 0x00, 7, 1, 2),
    "water-cooler": (0x0F, 0x00, 6, 2, 2),
    "wings": (None, 0x00, 11, 1, 1),
    # deprecated in favor of direction=backward
    "backwards-spectrum-wave": (0x02, 0x00, 2, 0, 0),
    "backwards-marquee-3": (0x03, 0x03, 2, 1, 1),
    "backwards-marquee-4": (0x03, 0x04, 2, 1, 1),
    "backwards-marquee-5": (0x03, 0x05, 2, 1, 1),
    "backwards-marquee-6": (0x03, 0x06, 2, 1, 1),
    "covering-backwards-marquee": (0x04, 0x00, 2, 1, 8),
    "backwards-moving-alternating-3": (0x05, 0x03, 4, 1, 2),
    "backwards-moving-alternating-4": (0x05, 0x04, 4, 1, 2),
    "backwards-moving-alternating-5": (0x05, 0x05, 4, 1, 2),
    "backwards-moving-alternating-6": (0x05, 0x06, 4, 1, 2),
    "backwards-rainbow-flow": (0x0B, 0x00, 2, 0, 0),
    "backwards-super-rainbow": (0x0C, 0x00, 2, 0, 0),
    "backwards-rainbow-pulse": (0x0D, 0x00, 2, 0, 0),
}

# A static value per channel that is somehow related to animation time and
# synchronization, although the specific mechanism is not yet understood.
# Could require information from `initialize`, but more testing is required.
_STATIC_VALUE = {
    0b001: 40,  # may result in long all-off intervals (FIXME?)
    0b010: 8,
    0b100: 1,
    0b111: 40,  # may result in long all-off intervals (FIXME?)
}

# Speed scale/timing bytes
# scale -> (slowest, slower, normal, faster, fastest)
_SPEED_VALUE = {
    0: ([0x32, 0x00], [0x32, 0x00], [0x32, 0x00], [0x32, 0x00], [0x32, 0x00]),
    1: ([0x50, 0x00], [0x3C, 0x00], [0x28, 0x00], [0x14, 0x00], [0x0A, 0x00]),
    2: ([0x5E, 0x01], [0x2C, 0x01], [0xFA, 0x00], [0x96, 0x00], [0x50, 0x00]),
    3: ([0x40, 0x06], [0x14, 0x05], [0xE8, 0x03], [0x20, 0x03], [0x58, 0x02]),
    4: ([0x20, 0x03], [0xBC, 0x02], [0xF4, 0x01], [0x90, 0x01], [0x2C, 0x01]),
    5: ([0x19, 0x00], [0x14, 0x00], [0x0F, 0x00], [0x07, 0x00], [0x04, 0x00]),
    6: ([0x28, 0x00], [0x1E, 0x00], [0x14, 0x00], [0x0A, 0x00], [0x04, 0x00]),
    7: ([0x32, 0x00], [0x28, 0x00], [0x1E, 0x00], [0x14, 0x00], [0x0A, 0x00]),
    8: ([0x14, 0x00], [0x14, 0x00], [0x14, 0x00], [0x14, 0x00], [0x14, 0x00]),
    9: ([0x00, 0x00], [0x00, 0x00], [0x00, 0x00], [0x00, 0x00], [0x00, 0x00]),
    10: ([0x37, 0x00], [0x28, 0x00], [0x19, 0x00], [0x0A, 0x00], [0x00, 0x00]),
    11: ([0x6E, 0x00], [0x53, 0x00], [0x39, 0x00], [0x2E, 0x00], [0x20, 0x00]),
}

_ANIMATION_SPEEDS = {
    "slowest": 0x0,
    "slower": 0x1,
    "normal": 0x2,
    "faster": 0x3,
    "fastest": 0x4,
}


class KrakenZ3(UsbDriver):
    """Fourth-generation Kraken Z liquid cooler."""

    SUPPORTED_DEVICES = [
        (
            0x1E71,
            0x3008,
            None,
            "NZXT Kraken Z (Z53, Z63 or Z73)",
            {
                "speed_channels": _SPEED_CHANNELS_KRAKENZ,
                "color_channels": _COLOR_CHANNELS_KRAKENZ,
            },
        )
    ]

    def __init__(self, device, description, speed_channels, color_channels, **kwargs):
        super().__init__(device, description, **kwargs)

        hidinfo = next(
            info
            for info in hid.enumerate(device.vendor_id, device.product_id)
            if info["serial_number"] == device.serial_number
        )
        assert hidinfo, "Could not find device in HID bus"

        self.hid_device = HidapiDevice(hid, hidinfo)
        self.hid_device.open()

        self._speed_channels = speed_channels
        self._color_channels = color_channels
        self.orientation = 0  # 0 = Normal, 1 = +90 degrees, 2 = 180 degrees, 3 = -90(270) degrees
        self.brightness = 50  # default 50%

    def initialize(self, direct_access=False, **kwargs):
        """Initialize the device and the driver.

        This method should be called every time the systems boots, resumes from
        a suspended state, or if the device has just been (re)connected.  In
        those scenarios, no other method, except `connect()` or `disconnect()`,
        should be called until the device and driver has been (re-)initialized.

        Returns None or a list of `(property, value, unit)` tuples, similarly
        to `get_status()`.
        """

        self.hid_device.clear_enqueued_reports()
        # request static infos
        self._hid_write([0x10, 0x01])  # firmware info
        self._hid_write([0x20, 0x03])  # lighting info
        self._hid_write([0x30, 0x01])  # lcd info

        # initialize
        update_interval = (lambda secs: 1 + round((secs - 0.5) / 0.25))(0.5)  # see issue #128
        self._hid_write([0x70, 0x02, 0x01, 0xB8, update_interval])
        self._hid_write([0x70, 0x01])

        status = []

        def parse_firm_info(msg):
            fw = f"{msg[0x11]}.{msg[0x12]}.{msg[0x13]}"
            status.append(("Firmware version", fw, ""))

        def parse_led_info(msg):
            channel_count = msg[14]
            assert channel_count == len(
                self._color_channels
            ), f"Unexpected number of color channels received: {channel_count}"

            def find(channel, accessory):
                offset = 15  # offset of first channel/first accessory
                acc_id = msg[offset + channel * HUE2_MAX_ACCESSORIES_IN_CHANNEL + accessory]
                return Hue2Accessory(acc_id) if acc_id else None

            for i in range(HUE2_MAX_ACCESSORIES_IN_CHANNEL):
                accessory = find(0, i)
                if not accessory:
                    break
                status.append((f"LED accessory {i + 1}", accessory, ""))

        def parse_lcd_info(msg):
            self.brightness = msg[0x18]
            self.orientation = msg[0x1A]
            status.append(("LCD Brightness", str(self.brightness) + "%", ""))
            status.append(("LCD Orientation", str(self.orientation * 90) + "°", ""))

        self._hid_read_until(
            {b"\x11\x01": parse_firm_info, b"\x21\x03": parse_led_info, b"\x31\x01": parse_lcd_info}
        )

        return sorted(status)

    def _hid_read(self):
        data = self.hid_device.read(_READ_LENGTH)
        return data

    def _hid_read_until(self, parsers):
        for _ in range(_MAX_READ_ATTEMPTS):
            msg = self.hid_device.read(_READ_LENGTH)
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                func(msg)
            if not parsers:
                return
        assert False, f"missing messages (attempts={_MAX_READ_ATTEMPTS}, missing={len(parsers)})"

    def _hid_read_until_return(self, parsers):
        for _ in range(_MAX_READ_ATTEMPTS):
            msg = self.hid_device.read(_READ_LENGTH)
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                return func(msg)
            if not parsers:
                return
        assert False, f"missing messages (attempts={_MAX_READ_ATTEMPTS}, missing={len(parsers)})"

    def _hid_write(self, data):
        padding = [0x0] * (_WRITE_LENGTH - len(data))
        self.hid_device.write(data + padding)

    def _hid_write_then_read(self, data):
        self._hid_write(data)
        return self._hid_read()

    def _bulk_write(self, data):
        padding = [0x0] * (_BULK_WRITE_LENGTH - len(data))
        self.device.write(0x2, data + padding)

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        self.hid_device.clear_enqueued_reports()
        self._hid_write([0x74, 0x01])
        msg = self._hid_read()
        return [
            (_STATUS_TEMPERATURE, msg[15] + msg[16] / 10, "°C"),
            (_STATUS_PUMP_SPEED, msg[18] << 8 | msg[17], "rpm"),
            (_STATUS_PUMP_DUTY, msg[19], "%"),
            (_STATUS_FAN_SPEED, msg[24] << 8 | msg[23], "rpm"),
            (_STATUS_FAN_DUTY, msg[25], "%"),
        ]

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to use a speed duty profile."""

        cid, dmin, dmax = self._speed_channels[channel]
        header = [0x72, cid, 0x00, 0x00]
        norm = normalize_profile(profile, _CRITICAL_TEMPERATURE)
        stdtemps = list(range(20, _CRITICAL_TEMPERATURE + 1))
        interp = [clamp(interpolate_profile(norm, t), dmin, dmax) for t in stdtemps]
        for temp, duty in zip(stdtemps, interp):
            _LOGGER.info(
                "setting %s PWM duty to %d%% for liquid temperature >= %d°C", channel, duty, temp
            )
        self._hid_write(header + interp)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""

        self.set_speed_profile(channel, [(0, duty), (_CRITICAL_TEMPERATURE - 1, duty)])

    def set_color(self, channel, mode, colors, speed="normal", direction="forward", **kwargs):
        """Set the color mode for a specific channel."""

        if "backwards" in mode:
            _LOGGER.warning("deprecated mode, move to direction=backward option")
            mode = mode.replace("backwards-", "")
            direction = "backward"

        cid = self._color_channels[channel]
        _, _, _, mincolors, maxcolors = _COLOR_MODES[mode]
        colors = [[g, r, b] for [r, g, b] in colors]
        if len(colors) < mincolors:
            raise ValueError(f"not enough colors for mode={mode}, at least {mincolors} required")
        elif maxcolors == 0:
            if colors:
                _LOGGER.warning("too many colors for mode=%s, none needed", mode)
            colors = [[0, 0, 0]]  # discard the input but ensure at least one step
        elif len(colors) > maxcolors:
            _LOGGER.warning("too many colors for mode=%s, dropping to %d", mode, maxcolors)
            colors = colors[:maxcolors]

        sval = _ANIMATION_SPEEDS[speed]
        self._write_colors(cid, mode, colors, sval, direction)

    def _write_colors(self, cid, mode, colors, sval, direction):
        mval, size_variant, speed_scale, mincolors, maxcolors = _COLOR_MODES[mode]
        color_count = len(colors)

        if "super-fixed" == mode or "super-breathing" == mode:
            color = list(itertools.chain(*colors)) + [0x00, 0x00, 0x00] * (maxcolors - color_count)
            speed_value = _SPEED_VALUE[speed_scale][sval]
            self._hid_write([0x22, 0x10, cid, 0x00] + color)
            self._hid_write([0x22, 0x11, cid, 0x00])
            self._hid_write(
                [0x22, 0xA0, cid, 0x00, mval]
                + speed_value
                + [0x08, 0x00, 0x00, 0x80, 0x00, 0x32, 0x00, 0x00, 0x01]
            )

        elif mode == "wings":  # wings requires special handling
            self._hid_write([0x22, 0x10, cid])  # clear out all independent LEDs
            self._hid_write([0x22, 0x11, cid])  # clear out all independent LEDs
            color_lists = {}
            color_lists[0] = colors[0] * 2
            color_lists[1] = [int(x // 2.5) for x in color_lists[0]]
            color_lists[2] = [int(x // 4) for x in color_lists[1]]
            color_lists[3] = [0x00] * 8
            speed_value = _SPEED_VALUE[speed_scale][sval]
            for i in range(8):  # send color scheme first, before enabling wings mode
                mod = 0x05 if i in [3, 7] else 0x01
                alt = [0x04, 0x84] if i // 4 == 0 else [0x84, 0x04]
                msg = (
                    [0x22, 0x20, cid, i, 0x04]
                    + speed_value
                    + [mod]
                    + [0x00] * 7
                    + [0x02]
                    + alt
                    + [0x00] * 10
                )
                self._hid_write(msg + color_lists[i % 4])
            self._hid_write([0x22, 0x03, cid, 0x08])  # this actually enables wings mode

        else:
            opcode = [0x2A, 0x04]
            address = [cid, cid]
            speed_value = _SPEED_VALUE[speed_scale][sval]
            header = opcode + address + [mval] + speed_value
            color = list(itertools.chain(*colors)) + [0, 0, 0] * (16 - color_count)

            if "marquee" in mode:
                backward_byte = 0x04
            elif mode == "starry-night" or "moving-alternating" in mode:
                backward_byte = 0x01
            else:
                backward_byte = 0x00

            backward_byte += map_direction(direction, 0, 0x02)

            if mode == "fading" or mode == "pulse" or mode == "breathing":
                mode_related = 0x08
            elif mode == "tai-chi":
                mode_related = 0x05
            elif mode == "water-cooler":
                mode_related = 0x05
                color_count = 0x01
            elif mode == "loading":
                mode_related = 0x04
            else:
                mode_related = 0x00

            static_byte = _STATIC_VALUE[cid]
            led_size = size_variant if mval == 0x03 or mval == 0x05 else 0x03
            footer = [backward_byte, color_count, mode_related, static_byte, led_size]
            self._hid_write(header + color + footer)

    def set_screen(self, mode, value, **kwargs):
        """
        Used with

        liquidctl [options] set lcd screen <mode>
        liquidctl [options] set lcd screen brightness <value>
        liquidctl [options] set lcd screen orientation (0|90|180|270)
        liquidctl [options] set lcd screen (static|gif) <path>
        """
        assert mode != None, f"No mode specified"

        # get orientation and brightness
        self._hid_write([0x30, 0x01])

        def parse_lcd_info(msg):
            self.brightness = msg[0x18]
            self.orientation = msg[0x1A]

        self._hid_read_until({b"\x31\x01": parse_lcd_info})

        if mode == "brightness":
            value_int = int(value)
            assert value_int >= 0 and value_int <= 100, "Invalid brightness value"
            self._hid_write([0x30, 0x02, 0x01, value_int, 0x0, 0x0, 0x1, self.orientation])
            return
        elif mode == "orientation":
            value_int = int(value)
            assert (
                value_int == 0 or value_int == 90 or value_int == 180 or value_int == 270
            ), "Invalid orientation value"
            self._hid_write([0x30, 0x02, 0x01, self.brightness, 0x0, 0x0, 0x1, int(value_int / 90)])
            return
        elif mode == "static":
            data = self._prepare_static_file(value, self.orientation)
            self.send_data(data, [0x02, 0x0, 0x0, 0x0, 0x0, 0x40, 0x06])
            return
        elif mode == "gif":
            data = self._prepare_gif_file(value, self.orientation)
            self.send_data(data, [0x01, 0x0, 0x0, 0x0] + list(len(data).to_bytes(3, "little")))
            return
        elif mode == "liquid":
            self._switch_bucket(0, 2)
            return

        raise TypeError("Invalid args")

    def _prepare_static_file(self, path, rotation):
        """
        path is the path to any image file
        Rotation is expected as 0 = no rotation, 1 = 90 degrees, 2 = 180 degrees, 3 = 270 degrees
        """
        img = Image.open(path)
        img = img.resize((320, 320))
        img = img.rotate(rotation * -90)
        data = img.getdata()
        result = []
        pixelDataIndex = 0
        for i in range(800):
            for p in range(0, 512, 4):
                result.append(data[pixelDataIndex][0])
                result.append(data[pixelDataIndex][1])
                result.append(data[pixelDataIndex][2])
                result.append(0)
                pixelDataIndex += 1
        return result

    def _prepare_gif_file(self, path, rotation):
        """
        path is the path of the gif file
        Rotation is expected as 0 = no rotation, 1 = 90 degrees, 2 = 180 degrees, 3 = 270 degrees
        Gifs are resized to 320x320 and rotated to match the desired orientation
        result is a bytesIo stream
        """
        img = Image.open(path)

        frames = ImageSequence.Iterator(img)

        def prepare_frames(frames):
            for frame in frames:
                resized = frame.copy()
                resized = resized.resize((320, 320))
                resized = resized.rotate(rotation * -90)
                yield resized

        frames = prepare_frames(frames)

        result_img = next(frames)  # Handle first frame separately
        result_img.info = img.info  # Copy sequence info

        result_bytes = io.BytesIO()
        result_img.save(
            result_bytes, format="GIF", save_all=True, append_images=list(frames), loop=0
        )

        return result_bytes.getvalue()

    def send_data(self, data, bulkInfo):
        """
        sends image or gif to device
        data is an array of bytes to write
        bulk info contains info about the transfer
        """
        self._hid_write_then_read([0x36, 0x03])  # unknown

        buckets = self._query_buckets()  # query all buckets and store their response

        self._hid_write_then_read([0x20, 0x03])  # unknown
        self._hid_write_then_read([0x74, 0x01])  # keepalive
        self._hid_write_then_read([0x70, 0x01])  # unknown
        self._hid_write_then_read([0x74, 0x01])  # keepalive

        bucketIndex = self._find_next_unoccupied_bucket(
            buckets
        )  # find the first unoccupied bucket in the list
        bucketIndex = self._prepare_bucket(
            bucketIndex if bucketIndex != -1 else 0, bucketIndex == -1
        )  # prepare bucket or find a more suitable one
        bucketMemoryStart = self._get_bucket_memory_offset(
            buckets, bucketIndex
        )  # extracts the bucket starting address

        packetCount = list(
            math.floor(
                (math.ceil(len(data) / _BULK_WRITE_LENGTH) + 1) / 2
            ).to_bytes(  # calculates the number of needed packets
                2, "little"
            )
        )

        self._setup_bucket(
            bucketIndex, bucketIndex + 1, bucketMemoryStart, packetCount
        )  # setup bucket for transfer
        self._hid_write_then_read([0x36, 0x01, bucketIndex])  # start data transfer

        self._bulk_write(
            [
                0x12,
                0xFA,
                0x01,
                0xE8,
                0xAB,
                0xCD,
                0xEF,
                0x98,
                0x76,
                0x54,
                0x32,
                0x10,
            ]  # first bulk write message contains a standard part and information about the transfer
            + bulkInfo
        )

        for i in range(0, len(data), _BULK_WRITE_LENGTH):  # start sending data in 512mb chunks
            self._bulk_write(list(data[i : i + _BULK_WRITE_LENGTH]))

        self._hid_write([0x36, 0x02])  # end data transfer
        if not self._switch_bucket(bucketIndex):  # switch to newly written bucket
            _LOGGER.warning("Failed to switch active bucket")
        self.device.release()  # release device when finished

    def _query_buckets(self):
        """
        Queries all 16 buckets and stores their response
        Response in structures as follow:
        - standard part (14 bytes) - unknown
        ---- following is all 0x0 if bucket is unoccupied
        - bucket index (1 byte)
        - asset index (1 byte) - same as bucket index + 1
        - 0x2 (1 byte) - unknown
        - starting memory address (2 bytes) - address sometimes changes so must be read from here
        - memory size (2 bytes) - size sometimes changes so must be read from here
        - 0x1 (1 byte) - unknown
        - 0x0|0x1 (1 byte) - most likely used/unused but could also be something else
        """
        buckets = {}
        for bI in range(0, 16):
            response = self._hid_write_then_read([0x30, 0x04, bI])  # query bucket
            buckets[bI] = response
        return buckets

    def _find_next_unoccupied_bucket(self, buckets):
        """
        finds the first available unoccupied bucket
        buckets are unoccupied when bytes 14 onward are 0x0
        returns -1 if unoccupied buckets are found
        """
        for bucketIndex, bucketInfo in buckets.items():
            if not any(bucketInfo[15:]):
                return bucketIndex
        return -1

    def _get_bucket_memory_offset(self, buckets, bucketIndex):
        """
        returns the memory start address
        memory offset is calculated as the offset of the previous bucket
        plus its size
        """
        if bucketIndex == 0x0:
            return [0x0, 0x0]
        bucket = buckets[bucketIndex - 1]
        return list(
            (
                int.from_bytes([bucket[17], bucket[18]], "little")
                + int.from_bytes([bucket[19], bucket[20]], "little")
            ).to_bytes(2, "little")
        )

    def _prepare_bucket(self, bucketIndex, bucketFilled):
        """
        if a bucket delete returns 0x9 then try next bucket
        if bucket already had data then delete it twice
        """
        assert bucketIndex < 16, "reached max bucket"
        delete_response = self._delete_bucket(bucketIndex)
        if not delete_response:
            return self._prepare_bucket(bucketIndex + 1, True)
        else:
            if bucketFilled:
                return self._prepare_bucket(bucketIndex, False)
        return bucketIndex

    def _delete_bucket(self, bucketIndex):
        """
        deletes bucket, returns true if successful, false otherwise
        """
        self._hid_write([0x32, 0x2, bucketIndex])

        def parse_delete_result(msg):
            return msg[14] == 0x1

        return self._hid_read_until_return({b"\x33\x02": parse_delete_result})

    def _switch_bucket(self, bucketIndex, mode=0x4):
        """
        switches active bucket, returns true if successful, false otherwise
        """
        response = self._hid_write_then_read([0x38, 0x1, mode, bucketIndex])
        return response[14] == 0x1

    def _setup_bucket(self, startBucketIndex, endBucketIndex, startingMemoryAddress, memorySize):
        """
        sets bucket for transmission, returns true if successful, false otherwise
        """
        response = self._hid_write_then_read(
            [
                0x32,
                0x1,
                startBucketIndex,
                endBucketIndex,
                startingMemoryAddress[0],
                startingMemoryAddress[1],
                memorySize[0],
                memorySize[1],
                0x1,
            ]
        )
        return response[14] == 0x1
