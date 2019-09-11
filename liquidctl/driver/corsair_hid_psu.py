"""liquidctl driver for Corsair HID PSUs.


Supported devices
-----------------

 - Corsair RMi (RM550i, RM650i, RM750i, RM850i or RM1000i)
 - Corsair HXi (HX550i, HX650i, HX750i, HX850i, HX1000i or HX1200i)


Supported features
------------------

 - [ ] general device monitoring
 - [ ] electrical input monitoring
 - [ ] electrical output monitoring
 - [ ] fan control
 - [ ] 12V multirail configuration


Port of corsaiRMi: incorporates or uses as reference work by notaz and realies,
under the terms of the BSD 3-Clause license.

Incorporates or uses as reference work by Sean Nelson, under the terms of the
GNU General Public License.

corsaiRMi
Copyright (c) notaz, 2016

liquidctl driver for Corsair HID PSUs
Copyright (C) 2019  Jonas Malaco
Copyright (C) 2019  each contribution's author

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

from liquidctl.driver.usb import UsbHidDriver


LOGGER = logging.getLogger(__name__)


class CorsairHidPsuDriver(UsbHidDriver):
    """liquidctl driver for Corsair HID PSUs."""

    SUPPORTED_DEVICES = [
        (0x1b1c, 0x1c09, None, 'Corsair RM550i (experimental)', {}),
        (0x1b1c, 0x1c0a, None, 'Corsair RM650i (experimental)', {}),
        (0x1b1c, 0x1c0b, None, 'Corsair RM750i (experimental)', {}),
        (0x1b1c, 0x1c0c, None, 'Corsair RM850i (experimental)', {}),
        (0x1b1c, 0x1c0d, None, 'Corsair RM1000i (experimental)', {}),
        (0x1b1c, 0x1c03, None, 'Corsair HX550i (experimental)', {}),
        (0x1b1c, 0x1c04, None, 'Corsair HX650i (experimental)', {}),
        (0x1b1c, 0x1c05, None, 'Corsair HX750i (experimental)', {}),
        (0x1b1c, 0x1c06, None, 'Corsair HX850i (experimental)', {}),
        (0x1b1c, 0x1c07, None, 'Corsair HX1000i (experimental)', {}),
        (0x1b1c, 0x1c08, None, 'Corsair HX1200i (experimental)', {}),
    ]

    def initialize(self, **kwargs):
        """Initialize the device."""
        pass

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """
        return []
