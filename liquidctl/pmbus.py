"""Constants and methods for interfacing with PMBus compliant devices.

References:

White, Robert V; 2010.  Power Systems Management Protocol Specification.  Part
II – Command Language.  Revision 1.2.
http://pmbus.org/Assets/PDFS/Public/PMBus_Specification_Part_II_Rev_1-2_20100906.pdf

White, Robert V; 2005.  Using the PMBus Protocol.
http://pmbus.org/Assets/Present/Using_The_PMBus_20051012.pdf

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

from enum import IntEnum, IntFlag, unique

@unique
class WriteBit(IntFlag):
    WRITE = 0x00
    READ = 0x01

@unique
class CommandCode(IntEnum):
    """Incomplete enumeration of the PMBus command codes."""

    PAGE = 0x00

    CLEAR_FAULTS = 0x03

    PAGE_PLUS_WRITE = 0x05
    PAGE_PLUS_READ = 0x06

    VOUT_MODE = 0x20

    READ_EIN = 0x86
    READ_EOUT = 0x87
    READ_VIN = 0x88
    READ_IIN = 0x89
    READ_VCAP = 0x8a
    READ_VOUT = 0x8b
    READ_IOUT = 0x8c
    READ_TEMPERATURE_1 = 0x8d
    READ_TEMPERATURE_2 = 0x8e
    READ_TEMPERATURE_3 = 0x8f
    READ_FAN_SPEED_1 = 0x90
    READ_FAN_SPEED_2 = 0x91
    READ_FAN_SPEED_3 = 0x92
    READ_FAN_SPEED_4 = 0x93
    READ_DUTY_CYCLE = 0x94
    READ_FREQUENCY = 0x95
    READ_POUT = 0x96
    READ_PIN = 0x97
    READ_PMBUS_REVISON = 0x98
    MFR_ID = 0x99
    MFR_MODEL = 0x9a
    MFR_REVISION = 0x9b
    MFR_LOCATION = 0x9c
    MFR_DATE = 0x9d
    MFR_SERIAL = 0x9e

    MFR_SPECIFIC_01 = 0xd1
    MFR_SPECIFIC_02 = 0xd2
    MFR_SPECIFIC_12 = 0xdc
    MFR_SPECIFIC_30 = 0xee
    MFR_SPECIFIC_44 = 0xfc


def linear_to_float(bytes, vout_exp=None):
    """Read PMBus Linear Data Format values.

    If `vout_exp` is None the value is assumed to be a 2-byte Linear Data
    Format value.  The fraction is stored in the lower 11 bits, in
    two's-complement, and the exponent is is stored in the upper 5 bits, also
    in two's-complement.

    Otherwise, the exponent is read from the lower 5 bits of `vout_exp` (which
    is assumed to be the output from VOUT_MOE) and the fraction is the unsigned
    2-byte integer in `bytes`.

    Per the SMBus specification, the lowest order byte is sent first (endianess
    is little).

    >>> linear_to_float([0x67, 0xe3])
    54.4375
    >>> linear_to_float([0x67, 0x03], vout_exp=0x1c)
    54.4375
    """
    tmp = int.from_bytes(bytes[:2], byteorder='little')
    if vout_exp is None:
        exp = tmp >> 11
        fra = tmp & 0x7ff
        if fra > 1023:
            fra = fra - 2048
    else:
        exp = vout_exp & 0x1f
        fra = tmp
    if exp > 15:
        exp = exp - 32
    return fra * 2**exp
