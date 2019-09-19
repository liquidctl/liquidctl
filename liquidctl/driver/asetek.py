"""USB drivers for fifth generation Asetek AIO liquid coolers.


Supported devices
-----------------

 - EVGA CLC (120 CL12, 240, 280 or 360); modern generic Asetek 690LC
 - NZXT Kraken X (X31, X41 or X61); legacy generic Asetek 690LC
 - NZXT Kraken X (X40 or X60); legacy generic Asetek 690LC
 - Corsair H80i GTX, H100i GTX or H110i GTX/experimental
 - Corsair H80i v2, H100i v2 or H115i/experimental


Supported features
------------------

 - initialization
 - connection and transaction life cycle
 - reporting of firmware version
 - monitoring of pump and fan speeds, and of liquid temperature
 - control of pump and fan speeds
 - control of lighting modes and colors


Copyright (C) 2018–2019  Jonas Malaco
Copyright (C) 2018–2019  each contribution's author

Incorporates or uses as reference work by Kristóf Jakab, Sean Nelson and Chris
Griffith, under the terms of the GNU General Public License.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import os
import sys

import appdirs
import usb

from liquidctl.driver.usb import UsbDeviceDriver
from liquidctl.util import color_from_str


LOGGER = logging.getLogger(__name__)

_FIXED_SPEED_CHANNELS = {    # (message type, minimum duty, maximum duty)
    'pump':  (0x13, 50, 100),  # min/max must correspond to _MIN/MAX_PUMP_SPEED_CODE
}
_VARIABLE_SPEED_CHANNELS = { # (message type, minimum duty, maximum duty)
    'fan':   (0x11, 0, 100)
}
_MAX_PROFILE_POINTS = 6
_CRITICAL_TEMPERATURE = 60
_HIGH_TEMPERATURE = 45
_MIN_PUMP_SPEED_CODE = 0x32
_MAX_PUMP_SPEED_CODE = 0x42
_READ_ENDPOINT = 0x82
_READ_LENGTH = 32
_READ_TIMEOUT = 2000
_WRITE_ENDPOINT = 0x2
_WRITE_TIMEOUT = 2000

_LEGACY_FIXED_SPEED_CHANNELS = {    # (message type, minimum duty, maximum duty)
    'fan':  (0x12, 0, 100),
    'pump':  (0x13, 50, 100),
}

# USBXpress specific control parameters; from the USBXpress SDK
# (Customization/CP21xx_Customization/AN721SW_Linux/silabs_usb.h)
_USBXPRESS_REQUEST = 0x02
_USBXPRESS_FLUSH_BUFFERS = 0x01
_USBXPRESS_CLEAR_TO_SEND = 0x02
_USBXPRESS_NOT_CLEAR_TO_SEND = 0x04
_USBXPRESS_GET_PART_NUM = 0x08

# Unknown control parameters; from Craig's libSiUSBXp and OpenCorsairLink
_UNKNOWN_OPEN_REQUEST = 0x00
_UNKNOWN_OPEN_VALUE = 0xFFFF

# Control request type
_USBXPRESS = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE


def _clamp(val, lo, hi, none=None, desc='value'):
    if val is None:
        return none
    elif val < lo:
        LOGGER.info('%s %s clamped to lo=%s, hi=%s', desc, val, lo, hi)
        return lo
    elif val > hi:
        LOGGER.info('%s %s clamped to lo=%s, hi=%s', desc, val, lo, hi)
        return hi
    else:
        return val


class CommonAsetekDriver(UsbDeviceDriver):
    """Common fuctions of fifth generation Asetek devices."""

    def _configure_flow_control(self, clear_to_send):
        """Set the software Clear to Send flow control policy for device."""
        LOGGER.debug('set clear to send = %s', clear_to_send)
        if clear_to_send:
            self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_CLEAR_TO_SEND)
        else:
            self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_NOT_CLEAR_TO_SEND)

    def _begin_transaction(self):
        """Begin a new transaction before writing to the device."""
        LOGGER.debug('begin transaction')
        self.device.claim()
        self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_FLUSH_BUFFERS)

    def _write(self, data):
        LOGGER.debug('write %s', ' '.join(format(i, '02x') for i in data))
        self.device.write(_WRITE_ENDPOINT, data, _WRITE_TIMEOUT)

    def _end_transaction_and_read(self):
        """End the transaction by reading from the device.

        According to the official documentation, as well as Craig's open-source
        implementation (libSiUSBXp), it should be necessary to check the queue
        size and read data in chunks.  However, leviathan and its derivatives
        seem to work fine without this complexity; we currently try the same
        approach.
        """
        msg = self.device.read(_READ_ENDPOINT, _READ_LENGTH, _READ_TIMEOUT)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        self.device.release()
        return msg

    def _configure_device(self, color1=[0, 0, 0], color2=[0, 0, 0], color3=[255, 0, 0],
                          alert_temp=_HIGH_TEMPERATURE, interval1=0, interval2=0,
                          blackout=False, fading=False, blinking=False, enable_alert=True):
        self._write([0x10] + color1 + color2 + color3
                    + [alert_temp, interval1, interval2, not blackout, fading,
                       blinking, enable_alert, 0x00, 0x01])

    def _prepare_profile(self, profile, min_duty, max_duty):
        opt = list(profile)
        size = len(opt)
        if size < 1:
            raise ValueError('At least one PWM point required')
        elif size > _MAX_PROFILE_POINTS:
            raise ValueError('Too many PWM points ({}), only 6 supported'.format(size))
        for i, (temp, duty) in enumerate(opt):
            opt[i] = (temp, _clamp(duty, min_duty, max_duty))
        missing = _MAX_PROFILE_POINTS - size
        if missing:
            # Some issues were observed when padding with (0°C, 0%), though
            # they were hard to reproduce.  So far it *seems* that in some
            # instances the device will store the last "valid" profile index
            # somewhere, and would need another call to initialize() to clear
            # that up.  Padding with (CRIT, 100%) appears to avoid all issues,
            # at least within the reasonable range of operating temperatures.
            LOGGER.info('filling missing %i PWM points with (60°C, 100%%)', missing)
            opt = opt + [(_CRITICAL_TEMPERATURE, 100)]*missing
        return opt

    def connect(self, **kwargs):
        """Connect to the device.

        Enables the device to send data to the host."""
        super().connect(**kwargs)
        self._configure_flow_control(clear_to_send=True)

    def initialize(self, **kwargs):
        """Initialize the device."""
        self._begin_transaction()
        self._configure_device()
        self._end_transaction_and_read()

    def disconnect(self, **kwargs):
        """Disconnect from the device.

        Implementation note: unlike SI_Close is supposed to do,¹ do not send
        _USBXPRESS_NOT_CLEAR_TO_SEND to the device.  This allows one program to
        disconnect without sotping reads from another.

        Surrounding device.read() with _USBXPRESS_[NOT_]CLEAR_TO_SEND would
        make more sense, but there seems to be a yet unknown minimum delay
        necessary for that to work well.

        ¹ https://github.com/craigshelley/SiUSBXp/blob/master/SiUSBXp.c
        """
        super().disconnect(**kwargs)


class AsetekDriver(CommonAsetekDriver):
    """USB driver for modern fifth generation Asetek coolers."""

    SUPPORTED_DEVICES = [
        (0x2433, 0xb200, None, 'Asetek 690LC (assuming EVGA CLC)', {}),
    ]

    @classmethod
    def find_supported_devices(cls, legacy_690lc=False, **kwargs):
        """Find and bind to compatible devices."""
        if legacy_690lc:
            return []
        return super().find_supported_devices(**kwargs)

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        self._begin_transaction()
        self._write([0x14, 0, 0, 0])
        msg = self._end_transaction_and_read()
        firmware = '{}.{}.{}.{}'.format(*tuple(msg[0x17:0x1b]))
        return [
            ('Liquid temperature', msg[10] + msg[14]/10, '°C'),
            ('Fan speed', msg[0] << 8 | msg[1], 'rpm'),
            ('Pump speed', msg[8] << 8 | msg[9], 'rpm'),
            ('Firmware version', firmware, '')
        ]

    def set_color(self, channel, mode, colors, time_per_color=1, time_off=None,
                  alert_threshold=_HIGH_TEMPERATURE, alert_color=[255, 0, 0],
                  speed=3, **kwargs):
        """Set the color mode for a specific channel."""
        # keyword arguments may have been forwarded from cli args and need parsing
        if isinstance(time_per_color, str):
            time_per_color = int(time_per_color)
        if isinstance(time_off, str):
            time_off = int(time_off)
        if isinstance(alert_threshold, str):
            alert_threshold = _clamp(int(alert_threshold), 0, 100)
        if isinstance(alert_color, str):
            alert_color = color_from_str(alert_color)
        colors = list(colors)
        self._begin_transaction()
        if mode == 'rainbow':
            if isinstance(speed, str):
                speed = int(speed)
            self._write([0x23, _clamp(speed, 1, 6, 'rainbow speed')])
            # make sure to clear blinking or... chaos
            self._configure_device(alert_temp=alert_threshold, color3=alert_color)
        elif mode == 'fading':
            self._configure_device(fading=True, color1=colors[0], color2=colors[1],
                                   interval1=_clamp(time_per_color, 1, 255, 'time per color'),
                                   alert_temp=alert_threshold, color3=alert_color)
            self._write([0x23, 0])
        elif mode == 'blinking':
            if time_off is None:
                time_off = time_per_color
            self._configure_device(blinking=True, color1=colors[0],
                                   interval1=_clamp(time_off, 1, 255, 'time off'),
                                   interval2=_clamp(time_per_color, 1, 255, 'time per color'),
                                   alert_temp=alert_threshold, color3=alert_color)
            self._write([0x23, 0])
        elif mode == 'fixed':
            self._configure_device(color1=colors[0], alert_temp=alert_threshold,
                                   color3=alert_color)
            self._write([0x23, 0])
        elif mode == 'blackout':  # stronger than just 'off', suppresses alerts and rainbow
            self._configure_device(blackout=True, alert_temp=alert_threshold, color3=alert_color)
        else:
            raise KeyError('Unknown lighting mode {}'.format(mode))
        self._end_transaction_and_read()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile."""
        mtype, dmin, dmax = _VARIABLE_SPEED_CHANNELS[channel]
        adjusted = self._prepare_profile(profile, dmin, dmax)
        for temp, duty in adjusted:
            LOGGER.info('setting %s PWM point: (%i°C, %i%%), device interpolated',
                        channel, temp, duty)
        temps, duties = map(list, zip(*adjusted))
        self._begin_transaction()
        self._write([mtype, 0] + temps + duties)
        self._end_transaction_and_read()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        if channel == 'fan':
            # While devices seem to recognize a specific channel for fixed fan
            # speeds (mtype == 0x12), its use can later conflict with custom
            # profiles.
            # Note for a future self: the conflict can be cleared with
            # *another* call to initialize(), i.e.  with another
            # configuration command.
            LOGGER.info('using a flat profile to set %s to a fixed duty', channel)
            self.set_speed_profile(channel, [(0, duty), (_CRITICAL_TEMPERATURE - 1, duty)])
            return
        mtype, dmin, dmax = _FIXED_SPEED_CHANNELS[channel]
        duty = _clamp(duty, dmin, dmax)
        total_levels = _MAX_PUMP_SPEED_CODE - _MIN_PUMP_SPEED_CODE + 1
        level = round((duty - dmin)/(dmax - dmin)*total_levels)
        effective_duty = round(dmin + level*(dmax - dmin)/total_levels)
        LOGGER.info('setting %s PWM duty to %i%% (level %i)', channel, effective_duty, level)
        self._begin_transaction()
        self._write([mtype, _MIN_PUMP_SPEED_CODE + level])
        self._end_transaction_and_read()


class LegacyAsetekDriver(CommonAsetekDriver):
    """USB driver for legacy fifth generation Asetek coolers."""

    SUPPORTED_DEVICES = [
        (0x2433, 0xb200, None, 'Asetek 690LC (assuming NZXT Kraken X) (experimental)', {}),
    ]

    @classmethod
    def find_supported_devices(cls, legacy_690lc=False, **kwargs):
        """Find and bind to compatible devices."""
        if not legacy_690lc:
            return []
        return super().find_supported_devices(**kwargs)

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        # compute path where fan/pump settings will be stored
        # [/run]/liquidctl/2433_b200_0100/usb1_12/
        ids = '{:04x}_{:04x}_{:04x}'.format(self.vendor_id, self.product_id, self.release_number)
        location = '{}_{}'.format(self.bus, '.'.join(map(str, self.port)))
        if sys.platform.startswith('linux') and os.path.isdir('/run'):
            basedir = '/run/liquidctl'
        else:
            basedir = appdirs.site_data_dir('liquidctl', 'jonasmalacofilho')
        self._data_path = os.path.join(basedir, ids, location)
        self._data_cache = {}
        LOGGER.debug('data directory for device is %s', self._data_path)

    def _load_integer(self, name):
        if name in self._data_cache:
            value = self._data_cache[name]
            LOGGER.debug('loaded %s=%s (from cache)', name, str(value))
            return value
        try:
            with open(os.path.join(self._data_path, name), mode='r') as f:
                data = f.read().strip()
                if len(data) == 0:
                    value = None
                else:
                    value = int(data)
                LOGGER.debug('loaded %s=%s', name, str(value))
        except OSError:
            LOGGER.debug('no data (file) found for %s', name)
            value = None
        finally:
            self._data_cache[name] = value
            return value

    def _store_integer(self, name, value):
        try:
            os.makedirs(self._data_path, mode=0o755)
        except FileExistsError:
            pass
        with open(os.path.join(self._data_path, name), mode='w') as f:
            if value is None:
                f.write('')
            else:
                f.write(str(value))
            self._data_cache[name] = value
            LOGGER.debug('stored %s=%s', name, str(value))

    def _set_all_fixed_speeds(self):
        self._begin_transaction()
        for channel in ['pump', 'fan']:
            mtype, dmin, dmax = _LEGACY_FIXED_SPEED_CHANNELS[channel]
            duty = _clamp(self._load_integer('{}_duty'.format(channel)), dmin, dmax, none=dmax)
            LOGGER.info('setting %s duty to %i%%', channel, duty)
            self._write([mtype, duty])
        return self._end_transaction_and_read()

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self._store_integer('pump_duty', None)
        self._store_integer('fan_duty', None)
        self._set_all_fixed_speeds()

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        msg = self._set_all_fixed_speeds()
        firmware = '{}.{}.{}.{}'.format(*tuple(msg[0x17:0x1b]))
        return [
            ('Liquid temperature', msg[10] + msg[14]/10, '°C'),
            ('Fan speed', msg[0] << 8 | msg[1], 'rpm'),
            ('Pump speed', msg[8] << 8 | msg[9], 'rpm'),
            ('Firmware version', firmware, '')
        ]

    def set_color(self, channel, mode, colors, time_per_color=None, time_off=None,
                  alert_threshold=_HIGH_TEMPERATURE, alert_color=[255, 0, 0],
                  **kwargs):
        """Set the color mode for a specific channel."""
        # keyword arguments may have been forwarded from cli args and need parsing
        if isinstance(time_per_color, str):
            time_per_color = int(time_per_color)
        if isinstance(time_off, str):
            time_off = int(time_off)
        if isinstance(alert_threshold, str):
            alert_threshold = _clamp(int(alert_threshold), 0, 100)
        if isinstance(alert_color, str):
            alert_color = color_from_str(alert_color)
        colors = list(colors)
        self._begin_transaction()
        if mode == 'fading':
            if time_per_color is None:
                time_per_color = 5
            self._configure_device(fading=True, color1=colors[0], color2=colors[1],
                                   interval1=_clamp(time_per_color, 1, 255, 'time per color'),
                                   alert_temp=alert_threshold, color3=alert_color)
        elif mode == 'blinking':
            if time_per_color is None:
                time_per_color = 1
            if time_off is None:
                time_off = time_per_color
            self._configure_device(blinking=True, color1=colors[0],
                                   interval1=_clamp(time_off, 1, 255, 'time off'),
                                   interval2=_clamp(time_per_color, 1, 255, 'time per color'),
                                   alert_temp=alert_threshold, color3=alert_color)
        elif mode == 'fixed':
            self._configure_device(color1=colors[0], alert_temp=alert_threshold,
                                   color3=alert_color)
        elif mode == 'blackout':  # stronger than just 'off', suppresses alerts and rainbow
            self._configure_device(blackout=True, alert_temp=alert_threshold, color3=alert_color)
        else:
            raise KeyError('Unsupported lighting mode {}'.format(mode))
        self._end_transaction_and_read()
        self._set_all_fixed_speeds()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        mtype, dmin, dmax = _LEGACY_FIXED_SPEED_CHANNELS[channel]
        duty = _clamp(duty, dmin, dmax)
        self._store_integer('{}_duty'.format(channel), duty)
        self._set_all_fixed_speeds()


class CorsairAsetekDriver(AsetekDriver):
    """USB driver for Corsair-branded fifth generation Asetek coolers."""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x0c02, None, 'Corsair Hydro H80i GTX (experimental)', {}),
        (0x1b1c, 0x0c03, None, 'Corsair Hydro H100i GTX (experimental)', {}),
        (0x1b1c, 0x0c07, None, 'Corsair Hydro H100i GTX (experimental)', {}),
        (0x1b1c, 0x0c08, None, 'Corsair Hydro H80i v2 (experimental)', {}),
        (0x1b1c, 0x0c09, None, 'Corsair Hydro H100i v2 (experimental)', {}),
        (0x1b1c, 0x0c0a, None, 'Corsair Hydro H115i (experimental)', {}),
    ]

    @classmethod
    def find_supported_devices(cls, legacy_690lc=None, **kwargs):
        """Find and bind to compatible devices."""
        # the modern driver overrides find_supported_devices and rigs it to
        # switch on --legacy-690lc, so we override it again
        return super().find_supported_devices(legacy_690lc=False, **kwargs)

    def set_color(self, channel, mode, colors, **kwargs):
        if mode == 'rainbow':
            raise KeyError('Unsupported lighting mode {}'.format(mode))
        super().set_color(channel, mode, colors, **kwargs)
