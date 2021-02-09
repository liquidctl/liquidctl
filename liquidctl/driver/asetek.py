"""liquidctl drivers for fifth generation Asetek 690LC liquid coolers.

Supported devices:

- EVGA CLC (120 CL12, 240, 280 or 360); modern generic Asetek 690LC
- NZXT Kraken X (X31, X41 or X61); legacy generic Asetek 690LC
- NZXT Kraken X (X40 or X60); legacy generic Asetek 690LC
- Corsair H80i GT, H100i GTX or H110i GTX
- Corsair H80i v2, H100i v2 or H115i

Copyright (C) 2018–2021  Jonas Malaco and contributors

Incorporates or uses as reference work by Kristóf Jakab, Sean Nelson
and Chris Griffith.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import logging

import usb

from liquidctl.driver.usb import UsbDriver
from liquidctl.error import NotSupportedByDevice
from liquidctl.keyval import RuntimeStorage
from liquidctl.util import clamp

_LOGGER = logging.getLogger(__name__)

_CMD_RUNTIME = 0x10
_CMD_PROFILE = 0x11
_CMD_OVERRIDE = 0x12
_CMD_PUMP_PWM = 0x13
_CMD_LUID = 0x14
_CMD_READ_ONLY_RUNTIME = 0x20
_CMD_STORE_SETTINGS = 0x21
_CMD_EXTERNAL_TEMPERATURE = 0x22

_FIXED_SPEED_CHANNELS = {    # (message type, minimum duty, maximum duty)
    'pump':  (_CMD_PUMP_PWM, 50, 100),  # min/max must correspond to _MIN/MAX_PUMP_SPEED_CODE
}
_VARIABLE_SPEED_CHANNELS = {  # (message type, minimum duty, maximum duty)
    'fan':   (_CMD_PROFILE, 0, 100)
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
    'fan':  (_CMD_OVERRIDE, 0, 100),
    'pump':  (_CMD_PUMP_PWM, 50, 100),
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
_UNKNOWN_OPEN_VALUE = 0xffff

# Control request type
_USBXPRESS = usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE


class _CommonAsetekDriver(UsbDriver):
    """Common methods for Asetek 690LC devices."""

    def _configure_flow_control(self, clear_to_send):
        """Set the software clear-to-send flow control policy for device."""
        _LOGGER.debug('set clear to send = %s', clear_to_send)
        if clear_to_send:
            self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_CLEAR_TO_SEND)
        else:
            self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_NOT_CLEAR_TO_SEND)

    def _begin_transaction(self):
        """Begin a new transaction before writing to the device."""
        _LOGGER.debug('begin transaction')
        self.device.claim()
        self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_FLUSH_BUFFERS)

    def _write(self, data):
        self.device.write(_WRITE_ENDPOINT, data, _WRITE_TIMEOUT)

    def _end_transaction_and_read(self):
        """End the transaction by reading from the device.

        According to the official documentation, as well as Craig's open-source
        implementation (libSiUSBXp), it should be necessary to check the queue
        size and read the data in chunks.  However, leviathan and its
        derivatives seem to work fine without this complexity; we also
        successfully follow this approach.
        """

        msg = self.device.read(_READ_ENDPOINT, _READ_LENGTH, _READ_TIMEOUT)
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
            raise ValueError('at least one PWM point required')
        elif size > _MAX_PROFILE_POINTS:
            raise ValueError(f'too many PWM points ({size}), only 6 supported')
        for i, (temp, duty) in enumerate(opt):
            opt[i] = (temp, clamp(duty, min_duty, max_duty))
        missing = _MAX_PROFILE_POINTS - size
        if missing:
            # Some issues were observed when padding with (0°C, 0%), though
            # they were hard to reproduce.  So far it *seems* that in some
            # instances the device will store the last "valid" profile index
            # somewhere, and would need another call to initialize() to clear
            # that up.  Padding with (CRIT, 100%) appears to avoid all issues,
            # at least within the reasonable range of operating temperatures.
            _LOGGER.info('filling missing %d PWM points with (60°C, 100%%)', missing)
            opt = opt + [(_CRITICAL_TEMPERATURE, 100)]*missing
        return opt

    def connect(self, **kwargs):
        """Connect to the device.

        Enables the device to send data to the host.
        """

        ret = super().connect(**kwargs)
        self._configure_flow_control(clear_to_send=True)
        return ret

    def initialize(self, **kwargs):
        """Initialize the device."""
        self._begin_transaction()
        self._configure_device()
        self._end_transaction_and_read()

    def disconnect(self, **kwargs):
        """Disconnect from the device.

        Implementation note: unlike SI_Close is supposed to do,¹ do not send
        _USBXPRESS_NOT_CLEAR_TO_SEND to the device.  This allows one program to
        disconnect without stopping reads from another.

        Surrounding device.read() with _USBXPRESS_[NOT_]CLEAR_TO_SEND would
        make more sense, but there seems to be a yet unknown minimum delay
        necessary for that to work reliably.

        ¹ https://github.com/craigshelley/SiUSBXp/blob/master/SiUSBXp.c
        """

        super().disconnect(**kwargs)


class Modern690Lc(_CommonAsetekDriver):
    """Modern fifth generation Asetek 690LC cooler."""

    SUPPORTED_DEVICES = [
        (0x2433, 0xb200, None, 'Asetek 690LC (assuming EVGA CLC)', {}),
    ]

    @classmethod
    def probe(cls, handle, legacy_690lc=False, **kwargs):
        if legacy_690lc:
            return
        yield from super().probe(handle, **kwargs)

    def downgrade_to_legacy(self):
        """Take the device handle and return a new Legacy690Lc instance for it.

        This method returns a new instance that takes the device handle from
        `self`.  Because of this, the caller should immediately discard `self`,
        as it is no longer valid to call any of its methods or access any of
        its properties.

        While it is sometimes possible to downgrade a device that has seen
        modern traffic since it booted, this will generally not work.
        Additionally, no attempt to disconnect from the device is made while
        downgrading the instance.

        Thus, callers are strongly advised to only call this function before
        connecting to the device from this instance and, in fact, before
        calling any other methods at all on the device, from any instance.

        Finally, this method is not yet considered stable and its signature
        and/or behavior may change.  Callers should follow the development of
        liquidctl and the stabilization of this API.
        """
        legacy = Legacy690Lc(self.device, self._description)
        self.device = None
        self._description = None
        return legacy

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        self._begin_transaction()
        self._write([_CMD_LUID, 0, 0, 0])
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
        colors = list(colors)
        self._begin_transaction()
        if mode == 'rainbow':
            if isinstance(speed, str):
                speed = int(speed)
            self._write([0x23, clamp(speed, 1, 6)])
            # make sure to clear blinking or... chaos
            self._configure_device(alert_temp=clamp(alert_threshold, 0, 100), color3=alert_color)
        elif mode == 'fading':
            self._configure_device(fading=True, color1=colors[0], color2=colors[1],
                                   interval1=clamp(time_per_color, 1, 255),
                                   alert_temp=clamp(alert_threshold, 0, 100), color3=alert_color)
            self._write([0x23, 0])
        elif mode == 'blinking':
            if time_off is None:
                time_off = time_per_color
            self._configure_device(blinking=True, color1=colors[0],
                                   interval1=clamp(time_off, 1, 255),
                                   interval2=clamp(time_per_color, 1, 255),
                                   alert_temp=clamp(alert_threshold, 0, 100), color3=alert_color)
            self._write([0x23, 0])
        elif mode == 'fixed':
            self._configure_device(color1=colors[0], alert_temp=clamp(alert_threshold, 0, 100),
                                   color3=alert_color)
            self._write([0x23, 0])
        elif mode == 'blackout':  # stronger than just 'off', suppresses alerts and rainbow
            self._configure_device(blackout=True, alert_temp=clamp(alert_threshold, 0, 100),
                                   color3=alert_color)
        else:
            raise KeyError(f'unknown lighting mode {mode}')
        self._end_transaction_and_read()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to follow a speed duty profile."""
        mtype, dmin, dmax = _VARIABLE_SPEED_CHANNELS[channel]
        adjusted = self._prepare_profile(profile, dmin, dmax)
        for temp, duty in adjusted:
            _LOGGER.info('setting %s PWM point: (%d°C, %d%%), device interpolated',
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
            _LOGGER.info('using a flat profile to set %s to a fixed duty', channel)
            self.set_speed_profile(channel, [(0, duty), (_CRITICAL_TEMPERATURE - 1, duty)])
            return
        mtype, dmin, dmax = _FIXED_SPEED_CHANNELS[channel]
        duty = clamp(duty, dmin, dmax)
        total_levels = _MAX_PUMP_SPEED_CODE - _MIN_PUMP_SPEED_CODE + 1
        level = round((duty - dmin)/(dmax - dmin)*total_levels)
        effective_duty = round(dmin + level*(dmax - dmin)/total_levels)
        _LOGGER.info('setting %s PWM duty to %d%% (level %d)', channel, effective_duty, level)
        self._begin_transaction()
        self._write([mtype, _MIN_PUMP_SPEED_CODE + level])
        self._end_transaction_and_read()


class Legacy690Lc(_CommonAsetekDriver):
    """Legacy fifth generation Asetek 690LC cooler."""

    SUPPORTED_DEVICES = [
        (0x2433, 0xb200, None, 'Asetek 690LC (assuming NZXT Kraken X) (experimental)', {}),
    ]

    @classmethod
    def probe(cls, handle, legacy_690lc=False, **kwargs):
        if not legacy_690lc:
            return
        yield from super().probe(handle, **kwargs)

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        # --device causes drivers to be instantiated even if they are later
        # discarded; defer instantiating the data storage until to connect()
        self._data = None

    def connect(self, runtime_storage=None, **kwargs):
        ret = super().connect(**kwargs)
        if runtime_storage:
            self._data = runtime_storage
        else:
            ids = f'vid{self.vendor_id:04x}_pid{self.product_id:04x}'
            loc = f'bus{self.bus}_port{"_".join(map(str, self.port))}'
            self._data = RuntimeStorage(key_prefixes=[ids, loc, 'legacy'])
        return ret

    def _set_all_fixed_speeds(self):
        self._begin_transaction()
        for channel in ['pump', 'fan']:
            mtype, dmin, dmax = _LEGACY_FIXED_SPEED_CHANNELS[channel]
            duty = clamp(self._data.load_int(f'{channel}_duty', default=dmax), dmin, dmax)
            _LOGGER.info('setting %s duty to %d%%', channel, duty)
            self._write([mtype, duty])
        return self._end_transaction_and_read()

    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        self._data.store_int('pump_duty', None)
        self._data.store_int('fan_duty', None)
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
        colors = list(colors)
        self._begin_transaction()
        if mode == 'fading':
            if time_per_color is None:
                time_per_color = 5
            self._configure_device(fading=True, color1=colors[0], color2=colors[1],
                                   interval1=clamp(time_per_color, 1, 255),
                                   alert_temp=clamp(alert_threshold, 0, 100), color3=alert_color)
        elif mode == 'blinking':
            if time_per_color is None:
                time_per_color = 1
            if time_off is None:
                time_off = time_per_color
            self._configure_device(blinking=True, color1=colors[0],
                                   interval1=clamp(time_off, 1, 255),
                                   interval2=clamp(time_per_color, 1, 255),
                                   alert_temp=clamp(alert_threshold, 0, 100), color3=alert_color)
        elif mode == 'fixed':
            self._configure_device(color1=colors[0], alert_temp=clamp(alert_threshold, 0, 100),
                                   color3=alert_color)
        elif mode == 'blackout':  # stronger than just 'off', suppresses alerts and rainbow
            self._configure_device(blackout=True, alert_temp=clamp(alert_threshold, 0, 100),
                                   color3=alert_color)
        else:
            raise KeyError(f'unsupported lighting mode {mode}')
        self._end_transaction_and_read()

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set channel to a fixed speed duty."""
        mtype, dmin, dmax = _LEGACY_FIXED_SPEED_CHANNELS[channel]
        duty = clamp(duty, dmin, dmax)
        self._data.store_int(f'{channel}_duty', duty)
        self._set_all_fixed_speeds()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Not supported by this device."""
        raise NotSupportedByDevice


class Hydro690Lc(Modern690Lc):
    """Corsair-branded fifth generation Asetek 690LC cooler."""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x0c02, None, 'Corsair Hydro H80i GT (experimental)', {}),
        (0x1b1c, 0x0c03, None, 'Corsair Hydro H100i GTX (experimental)', {}),
        (0x1b1c, 0x0c07, None, 'Corsair Hydro H110i GTX (experimental)', {}),
        (0x1b1c, 0x0c08, None, 'Corsair Hydro H80i v2', {}),
        (0x1b1c, 0x0c09, None, 'Corsair Hydro H100i v2', {}),
        (0x1b1c, 0x0c0a, None, 'Corsair Hydro H115i', {}),
    ]

    @classmethod
    def probe(cls, handle, legacy_690lc=False, **kwargs):
        # the modern driver overrides probe and rigs it to switch on
        # --legacy-690lc, so we override it again
        return super().probe(handle, legacy_690lc=False, **kwargs)

    def set_color(self, channel, mode, colors, **kwargs):
        """Set the color mode for a specific channel."""
        if mode == 'rainbow':
            raise KeyError(f'unsupported lighting mode {mode}')
        super().set_color(channel, mode, colors, **kwargs)


# deprecated aliases
AsetekDriver = Modern690Lc
LegacyAsetekDriver = Legacy690Lc
CorsairAsetekDriver = Hydro690Lc
