"""USB driver for fifth generation Asetek coolers.


Supported devices
-----------------

 - [⋯] NZXT Kraken X (X31, X41 or X61)
 - [ ] EVGA CLC (120 CL12, 240 or 280)


Driver features
---------------

 - [⋯] initialization
 - [⋯] connection and transaction life cycle
 - [⋯] reporting of firmware version
 - [⋯] monitoring of pump and fan speeds, and of liquid temperature
 - [⋯] control of pump and fan speeds
 - [✕] control of lighting modes and colors


Copyright (C) 2018–2019  Jonas Malaco
Copyright (C) 2018–2019  each contribution's author

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

import usb

import liquidctl.util
from liquidctl.driver.usb import UsbDeviceDriver


LOGGER = logging.getLogger(__name__)

_FIXED_SPEED_CHANNELS = {    # (message type, minimum duty, maximum duty)
    'fan':   (0x12, 30, 100),
    'pump':  (0x13, 30, 100),
}
_VARIABLE_SPEED_CHANNELS = { # (message type, minimum duty, maximum duty)
    'fan':   (0x11, 30, 100)
}
_MAX_PROFILE_POINTS = 6
_CRITICAL_TEMPERATURE = 60
_READ_ENDPOINT = 0x82
_READ_LENGTH = 32
_READ_TIMEOUT = 2000
_WRITE_ENDPOINT = 0x2
_WRITE_TIMEOUT = 2000

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


class AsetekDriver(UsbDeviceDriver):
    """USB driver for fifth generation Asetek coolers."""

    SUPPORTED_DEVICES = [
        (0x2433, 0xb200, None, 'NZXT Kraken X (X31, X41 or X61) (experimental)', {}),  # TODO also EVGA CLC (120 CL12, 240 or 280)
    ]

    def connect(self, **kwargs):
        """Connect to the device.

        Attaches to the kernel driver (or, on Linux, replaces it) and, if no
        configuration has been set, configures the device to use the first
        available one.  Finally, opens the device.
        """
        super().connect()
        try:
            self._open()
        except usb.core.USBError as err:
            LOGGER.warning('report: failed to open right away, will close first')
            LOGGER.debug(err, exc_info=True)
            self._close()
            self._open()

    def disconnect(self, **kwargs):
        """Disconnect from the device.

        Closes the device, cleans up and, on Linux, reattaches the
        previously used kernel driver.
        """
        self._close()
        super().disconnect()

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of (key, value, unit) tuples.
        """
        self._begin_transaction()
        self._send_dummy_command()
        msg = self._end_transaction_and_read()
        firmware = '{}.{}.{}.{}'.format(*tuple(msg[0x17:0x1b]))
        return [
            ('Liquid temperature', msg[10] + msg[14]/10, '°C'),  # TODO sensible decimal?
            ('Fan speed', msg[0] << 8 | msg[1], 'rpm'),
            ('Pump speed', msg[8] << 8 | msg[9], 'rpm'),
            ('Firmware version', firmware, '')  # TODO sensible firmware version?
        ]

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set channel to use a speed profile."""
        mtype, dmin, dmax = _VARIABLE_SPEED_CHANNELS[channel]
        opt_profile = self._prepare_profile(profile, dmin, dmax)
        for temp, duty in opt_profile:
            LOGGER.info('setting %s PWM duty to %i%% for liquid temperature >= %i°C',
                        channel, duty, temp)
        temps, duties = map(list, zip(*opt_profile))
        self._begin_transaction()
        # note: it might be necessary to call _send_dummy_command first
        self._write([mtype, 0] + temps + duties)
        self._end_transaction_and_read()

    def _prepare_profile(self, profile, min_duty, max_duty):
        norm = liquidctl.util.normalize_profile(profile, _CRITICAL_TEMPERATURE)
        opt = liquidctl.util.autofill_profile(norm, _MAX_PROFILE_POINTS)
        for i, (temp, duty) in enumerate(opt):
            if duty < min_duty:
                opt[i] = (temp, min_duty)
            elif duty > max_duty:
                opt[i] = (temp, max_duty)
        return opt

    def set_fixed_speed(self, channel, speed, **kwargs):
        """Set (pseudo) channel to a fixed speed."""
        if channel == 'sync':  # TODO remove once setting independently is working well
            self._begin_transaction()
            self._send_fixed_speed('pump', speed)
            self._send_fixed_speed('fan', speed)
            self._end_transaction_and_read()
        elif _FIXED_SPEED_CHANNELS[channel]:
            self._begin_transaction()
            if channel == 'fan':  # TODO check order of dummy and real command
                self._send_dummy_command()
            self._send_fixed_speed(channel, speed)
            if channel == 'pump':
                self._send_dummy_command()
            self._end_transaction_and_read()

    def _send_fixed_speed(self, channel, speed):
        """Set channel to a fixed speed."""
        mtype, smin, smax = _FIXED_SPEED_CHANNELS[channel]
        if speed < smin:
            speed = smin
        elif speed > smax:
            speed = smax
        LOGGER.info('setting %s PWM duty to %i%%', channel, speed)
        self._write([mtype, speed])

    def _open(self):
        """Open the USBXpress device."""
        LOGGER.debug('open device')
        try:
            pre = 'control: open'
            self.device.ctrl_transfer(_USBXPRESS, _UNKNOWN_OPEN_REQUEST, _UNKNOWN_OPEN_VALUE)
            pre = 'clear halt: read'
            self.device.clear_halt(_READ_ENDPOINT)
            pre = 'clear halt: write'
            self.device.clear_halt(_WRITE_ENDPOINT)
        except usb.core.USBError as err:
            LOGGER.warning('report: failed to (pre) open (%s), ignoring', pre)
            LOGGER.debug(err, exc_info=True)
        self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_CLEAR_TO_SEND)

    def _close(self):
        """Close the USBXpress device."""
        LOGGER.debug('close device')
        self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_NOT_CLEAR_TO_SEND)

    def _begin_transaction(self):
        """Begin a new transaction before writing to the device."""
        LOGGER.debug('begin transaction')
        self.device.ctrl_transfer(_USBXPRESS, _USBXPRESS_REQUEST, _USBXPRESS_FLUSH_BUFFERS)

    def _end_transaction_and_read(self):
        """End the transaction by reading from the device.

        According to the official documentation, as well as Craig's open-source
        implementation (libSiUSBXp), it should be necessary to check the queue
        size and read data in chunks.  However, leviathan and its derivatives
        seem to work fine without this complexity; we are currently try the
        same approach.
        """
        msg = self.device.read(_READ_ENDPOINT, _READ_LENGTH, _READ_TIMEOUT)
        LOGGER.debug('received %s', ' '.join(format(i, '02x') for i in msg))
        self.device.release()
        return msg

    def _send_dummy_command(self):
        """Send a dummy command to allow get_status to succeed.

        Reading from the device appears to require writing to it first.  We are
        not aware of any command specifically for getting data.  Instead, this
        uses a color change command, turning it off.
        """
        self._write([
            0x10,  # cmd: color change
            0x00, 0x00, 0x00,  # main color: #000000
            0x00, 0x00, 0x00,  # alt. color: #000000
            0x00, 0x00, 0x00, 0x3c,  # constant
            0x00, 0x00,  # interval: 0
            0x01, 0x00, 0x00,  # mode: off
            0x01, 0x00, 0x01  # constant
            ])

    def _write(self, data):
        LOGGER.debug('write %s', ' '.join(format(i, '02x') for i in data))
        self.device.write(_WRITE_ENDPOINT, data, _WRITE_TIMEOUT)

