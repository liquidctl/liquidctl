"""liquidctl drivers for fourth-generation NZXT Kraken X and Z liquid coolers.

Supported devices:

- NZXT Kraken X (X53, X63 and Z73)
- NZXT Kraken Z (Z53, Z63 and Z73)

Copyright (C) 2020–2022  Tom Frey, Jonas Malaco, Shady Nawara and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging
from time import sleep

from liquidctl.driver.usb import UsbDriver, UsbHidDriver
from liquidctl.util import normalize_profile, interpolate_profile, clamp, \
                           Hue2Accessory, HUE2_MAX_ACCESSORIES_IN_CHANNEL, \
                           map_direction

from PIL import Image
from PIL import GifImagePlugin

_LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64
_BULK_WRITE_LENGTH = 512
_MAX_READ_ATTEMPTS = 12

_STATUS_TEMPERATURE = 'Liquid temperature'
_STATUS_PUMP_SPEED = 'Pump speed'
_STATUS_PUMP_DUTY = 'Pump duty'
_STATUS_FAN_SPEED = 'Fan speed'
_STATUS_FAN_DUTY = 'Fan duty'

# Available speed channels for model Z coolers
# name -> (channel_id, min_duty, max_duty)
# TODO adjust min duty values to what the firmware enforces
_SPEED_CHANNELS_KRAKENZ = {
    'pump': (0x1, 20, 100),
    'fan': (0x2, 0, 100),
}

_CRITICAL_TEMPERATURE = 59

# Available color channels and IDs for model Z coolers
_COLOR_CHANNELS_KRAKENZ = {
    'external': 0b001,
    'screen': 0b1111
}

class KrakenZ3(UsbDriver):
    """Fourth-generation Kraken Z liquid cooler."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x3008, None, 'NZXT Kraken Z (Z53, Z63 or Z73)', {
            'speed_channels': _SPEED_CHANNELS_KRAKENZ,
            'color_channels': _COLOR_CHANNELS_KRAKENZ,
        })
    ]

    def __init__(self, device, description, speed_channels, color_channels, **kwargs):
        super().__init__(device, description, **kwargs)
        self._speed_channels = speed_channels
        self._color_channels = color_channels
        self.orientation = 0 # 0 = Normal, 1 = +90 degrees, 2 = 180 degrees, 3 = -90(270) degrees
        self.brightness = 50 # default 50%
        self.initialized = False


    def initialize(self, direct_access=False, **kwargs):
        """Initialize the device and the driver.

        This method should be called every time the systems boots, resumes from
        a suspended state, or if the device has just been (re)connected.  In
        those scenarios, no other method, except `connect()` or `disconnect()`,
        should be called until the device and driver has been (re-)initialized.

        Returns None or a list of `(property, value, unit)` tuples, similarly
        to `get_status()`.
        """

        # request static infos
        self._write([0x10, 0x01])  # firmware info
        self._write([0x20, 0x03])  # lighting info
        self._write([0x30, 0x01])  # lcd info

        # initialize
        update_interval = (lambda secs: 1 + round((secs - .5) / .25))(.5)  # see issue #128
        self._write([0x70, 0x02, 0x01, 0xb8, update_interval])
        self._write([0x70, 0x01])

        status = []

        def parse_firm_info(msg):
            fw = f'{msg[0x11]}.{msg[0x12]}.{msg[0x13]}'
            status.append(('Firmware version', fw, ''))

        def parse_led_info(msg):
            channel_count = msg[14]
            assert channel_count + 1 == len(self._color_channels) - ('sync' in self._color_channels), \
                   f'Unexpected number of color channels received: {channel_count}'

            def find(channel, accessory):
                offset = 15  # offset of first channel/first accessory
                acc_id = msg[offset + channel * HUE2_MAX_ACCESSORIES_IN_CHANNEL + accessory]
                return Hue2Accessory(acc_id) if acc_id else None

            for i in range(HUE2_MAX_ACCESSORIES_IN_CHANNEL):
                accessory = find(0, i)
                if not accessory:
                    break
                status.append((f'LED accessory {i + 1}', accessory, ''))

        
        def parse_lcd_info(msg):
            self.brightness = msg[0x18]
            on = msg[0x1a] #orientation number
            self.orientation = on
            orientation_str = "NORMAL" if on == 0 else "ROTATION90" if on == 1 else "ROTATION180" if on == 2 else "ROTATION270" if on == 3 else "NORMAL"
            status.append(('LCD Brightness', str(self.brightness), ''))
            status.append(('LCD Orientation', orientation_str, ''))

        self._read_until({b'\x11\x01': parse_firm_info, b'\x21\x03': parse_led_info, b'\x31\x01': parse_lcd_info})
        self.initialized = True
        return sorted(status)

    def _read(self):
        data = self.device.read(0x81, _READ_LENGTH)
        return data

    def _read_until(self, parsers):
        for _ in range(_MAX_READ_ATTEMPTS):
            msg = self.device.read(0x81, _READ_LENGTH)
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                func(msg)
            if not parsers:
                return
        assert False, f'missing messages (attempts={_MAX_READ_ATTEMPTS}, missing={len(parsers)})'

    def _read_until_return(self, parsers):
        for _ in range(_MAX_READ_ATTEMPTS):
            msg = self.device.read(0x81, _READ_LENGTH)
            prefix = bytes(msg[0:2])
            func = parsers.pop(prefix, None)
            if func:
                return func(msg)
            if not parsers:
                return
        assert False, f'missing messages (attempts={_MAX_READ_ATTEMPTS}, missing={len(parsers)})'

    def _write(self, data):
        padding = [0x0] * (_WRITE_LENGTH - len(data))
        self.device.write(0x1, data + padding)

    def _bulk_write(self, data):
        padding = [0x0] * (_BULK_WRITE_LENGTH - len(data))
        self.device.write(0x2, data + padding)

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        self.device.clear_enqueued_reports()
        self._write([0x74, 0x01])
        msg = self._read()
        return [
            (_STATUS_TEMPERATURE, msg[15] + msg[16] / 10, '°C'),
            (_STATUS_PUMP_SPEED, msg[18] << 8 | msg[17], 'rpm'),
            (_STATUS_PUMP_DUTY, msg[19], '%'),
            (_STATUS_FAN_SPEED, msg[24] << 8 | msg[23], 'rpm'),
            (_STATUS_FAN_DUTY, msg[25], '%'),
        ]

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to use a speed duty profile."""

        cid, dmin, dmax = self._speed_channels[channel]
        header = [0x72, cid, 0x00, 0x00]
        norm = normalize_profile(profile, _CRITICAL_TEMPERATURE)
        stdtemps = list(range(20, _CRITICAL_TEMPERATURE + 1))
        interp = [clamp(interpolate_profile(norm, t), dmin, dmax) for t in stdtemps]
        for temp, duty in zip(stdtemps, interp):
            _LOGGER.info('setting %s PWM duty to %d%% for liquid temperature >= %d°C',
                         channel, duty, temp)
        self._write(header + interp)

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""

        self.set_speed_profile(channel, [(0, duty), (_CRITICAL_TEMPERATURE - 1, duty)])

    def set_color(self, channel, mode, color, speed='normal', direction='forward', **kwargs):
        """Set the color mode for a specific channel."""
        """supported channel is screen,
            mode is an array ["config|static", "path to image|brightness|orientation", "brightness,orientation value"]
            color is unused,
            speed is unused,
            direction is unused
            """
        assert channel == "screen", f'Invalid Channel: {channel}'

        # get orientation and brightness
        if not self.initialized:
            self._write([0x30, 0x01])
            def parse_lcd_info(msg):
                self.brightness = msg[0x18]
                on = msg[0x1a] #orientation number
                self.orientation = on
            self._read_until({b'\x31\x01': parse_lcd_info})

        if len(mode) > 1:
            if mode[0].lower() == "config" and len(mode) > 2:
                if mode[1].lower() == "brightness":
                    self._write([0x30, 0x02, 0x01, int(mode[2]), 0x0, 0x0,0x1, self.orientation])
                    return
                elif mode[1].lower() == "orientation":
                    self._write([0x30, 0x02, 0x01, self.brightness, 0x0, 0x0, 0x1, int(mode[2])])
                    return
            elif mode[0].lower() == "liquid":
                self._switch_bucket(0, 2)
            elif mode[0].lower() == "static":
                data = self._prepare_static_file(mode[1], self.orientation)
                self._send_data(data, [0x02, 0x0, 0x0, 0x0, 0x0, 0x40, 0x06])
            elif mode[0].lower() == "gif":
                self._prepare_gif_file(mode[1], self.orientation, self._send_static_image)

    def _prepare_static_file(self, path, rotation):
        '''
        Rotation is expected as 0 = no rotation, 1 = 90 degrees, 2 = 180 degrees, 3 = 270 degrees
        '''
        try: 
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
        except IOError:
            pass

    def _prepare_gif_file(self, path, rotation, frame_callback):
        '''
        Rotation is expected as 0 = no rotation, 1 = 90 degrees, 2 = 180 degrees, 3 = 270 degrees
        '''
        try: 
            img = Image.open(path)
            img = img.resize((320, 320))
            img = img.rotate(rotation * -90)
            for f in range(0,img.n_frames):
                img.seek(f)
                frame_callback(img.getdata())
        except IOError:
            pass 
    
            

    def _send_data(self, data, bulk_info):
        '''
        expects a PIL data type or other nested array[[],[]]
        '''
        self._write([0x36, 0x03]) # unknown
        bucketIndex = self._find_next_unoccupied_bucket()
        bucketIndex = self._prepare_bucket(bucketIndex if bucketIndex != -1 else 0, bucketIndex == -1)
        self._write([0x20, 0x03]) # unknown
        self._write([0x74, 0x01]) # keepalive
        self._write([0x70, 0x01]) # unknown
        self._write([0x74, 0x01]) # keepalive
        self._setup_bucket(bucketIndex, bucketIndex + 1)
        sleep(0.1)
        self._write([0x36, 0x01, bucketIndex]) # start frame transfer
        sleep(0.1)
        self._bulk_write([0x12, 0xfa, 0x01, 0xe8, 0xab, 0xcd, 0xef, 0x98, 
        0x76, 0x54, 0x32, 0x10] + bulk_info)
        sleep(0.001)
        for i in range(0, len(data), _BULK_WRITE_LENGTH):
            x = i
            self._bulk_write(data[x:x+_BULK_WRITE_LENGTH])
        sleep(0.001)
        self._write([0x36, 0x02]) # end frame transfer
        sleep(0.1)
        self._switch_bucket(bucketIndex)
        sleep(0.01)
        self._write([0x74, 0x01]) # keepalive

    def _find_next_unoccupied_bucket(self, startingBucket = 0):
        buckets = {}
        for bI in range(startingBucket, 15):
            self._write([0x30, 0x04, bI]) # query bucket
            response = self._read()
            buckets[bI] = (response[16], response[22])
            if response[16] and response[22] == 0:
                return bI
        return -1
    
    def _prepare_bucket(self, bucketIndex, bucketFilled):
        '''
        if a bucket delete returns 0x9 then try next bucket
        if bucket already had data then delete it twice
        '''
        assert bucketIndex < 16, "reached max bucket"
        delete_response = self._delete_bucket(bucketIndex)
        if not delete_response:
            return self._prepare_bucket(bucketIndex + 1, True)
        else:
            if bucketFilled:
                return self._prepare_bucket(bucketIndex, False)
        return bucketIndex

    def _delete_bucket(self, bucketIndex):
        self._write([0x32, 0x2, bucketIndex])
        def parse_delete_result(msg):
            return msg[14] == 0x1

        return self._read_until_return({b'\x33\x02': parse_delete_result})

    def _switch_bucket(self, bucketIndex, mode = 0x4):
        self._write([0x38, 0x1, mode, bucketIndex])

    def _get_memory_start_slot(self, bucketIndex):
        return 400 * bucketIndex
    
    def _setup_bucket(self, startBucketIndex, endBucketIndex):
        startMemoryAddress = self._get_memory_start_slot(startBucketIndex)
        self._write([0x32, 0x1, startBucketIndex, endBucketIndex, startMemoryAddress & 0xff, startMemoryAddress >> 8, 0x90, 0x1, 0x1])
        

