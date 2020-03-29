"""liquidctl driver for CoolIT Platinum coolers for Corsair.

 Supported devices
 -----------------

  - [ ] NZXT Kraken X53
  - [ ] NZXT Kraken X63
  - [✓] NZXT Kraken X73

 Supported features
 ------------------

  - [ ] general monitoring
  - [ ] pump speed control
  - [ ] lighting control

 ---

 liquidctl driver for Kraken X3 devices from NZXT.
 Copyright (C) 2020–2020  Jonas Malaco
 Copyright (C) 2020–2020  each contribution's author

 This file is part of liquidctl.

 liquidctl is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 liquidctl is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
 """

import logging

from liquidctl.driver.usb import UsbHidDriver

LOGGER = logging.getLogger(__name__)

_READ_LENGTH = 64
_WRITE_LENGTH = 64


class KrakenThreeX(UsbHidDriver):
    """liquidctl driver for Kraken X3 devices from NZXT."""

    SUPPORTED_DEVICES = [
        (0x1e71, 0x2007, None, 'NZXT Kraken X3 Pump (X53, X63 or X73) (experimental)', {})
    ]