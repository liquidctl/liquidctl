"""Assorted utilities used by drivers and the CLI.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import colorsys
import logging
from ast import literal_eval
from enum import Enum, EnumMeta, unique
from typing import Optional

from functools import lru_cache

import crcmod.predefined

from liquidctl.error import UnsafeFeaturesNotEnabled

_LOGGER = logging.getLogger(__name__)

HUE2_MAX_ACCESSORIES_IN_CHANNEL = 6


@unique
class Hue2Accessory(Enum):
    """Mapping of HUE 2 accessory IDs and names.

    >>> Hue2Accessory(4)
    <Hue2Accessory.HUE2_LED_STRIP_300: 4>
    >>> str(Hue2Accessory(4))
    'HUE 2 LED Strip 300 mm'

    Unknown IDs are automatically translated to equivalent pseudo-names.

    >>> Hue2Accessory(59)
    <Hue2Accessory.UNKNOWN_59: 59>
    >>> Hue2Accessory(59).value == Hue2Accessory(59).value
    True
    >>> Hue2Accessory(59) != Hue2Accessory(58)
    True
    """

    HUE_PLUS_LED_STRIP = (0x01, 'HUE+ LED Strip')
    AER_RGB1_FAN = (0x02, 'AER RGB 1')
    HUE2_LED_STRIP_300 = (0x04, 'HUE 2 LED Strip 300 mm')
    HUE2_LED_STRIP_250 = (0x05, 'HUE 2 LED Strip 250 mm')
    HUE2_LED_STRIP_200 = (0x06, 'HUE 2 LED Strip 200 mm')
    HUE2_CABLE_COMB = (0x07, 'HUE 2 Cable Comb')
    HUE2_UNDERGLOW_300 = (0x09, 'HUE 2 Underglow 300 mm')
    HUE2_UNDERGLOW_200 = (0x0a, 'HUE 2 Underglow 200 mm')
    AER_RGB2_120 = (0x0b, 'AER RGB 2 120 mm')
    AER_RGB2_140 = (0x0c, 'AER RGB 2 140 mm')
    KRAKENX_GEN4_RING = (0x10, 'Kraken X (X53, X63 or X73) Pump Ring')
    KRAKENX_GEN4_LOGO = (0x11, 'Kraken X (X53, X63 or X73) Pump Logo')
    F120_RGB = (0x13, 'F120 RGB')
    F140_RGB = (0x14, 'F140 RGB')

    def __new__(cls, value, pretty_name):
        member = object.__new__(cls)
        member.pretty_name = pretty_name
        member._value_ = value
        return member

    @classmethod
    def _missing_(cls, value):
        dummy = object.__new__(cls)
        dummy.pretty_name = 'Unknown'
        dummy._name_ = f'UNKNOWN_{value}'
        dummy._value_ = value
        return dummy

    def __str__(self):
        return self.pretty_name

    def __eq__(self, other):
        return self.value == other.value


class LazyHexRepr:
    """Wrap an indexed collection of bytes with a lazy hex __repr__.

    This is useful for logging, which uses `%` string formatting to lazily
    generate the messages, only when needed.

    >>> '%r' % LazyHexRepr(b'abc')
    '61:62:63'

    Start and end indices may also be specified.

    >>> '%r' % LazyHexRepr(b'abc', start=1)
    '62:63'
    >>> '%r' % LazyHexRepr(b'abc', end=-1)
    '61:62'
    """
    def __init__(self, data, start=None, end=None, sep=':'):
        self.data = data
        self.start = start
        self.end = end
        self.sep = sep

    def __repr__(self):
        hexvals = map(lambda x: f'{x:02x}', self.data[self.start: self.end])
        return self.sep.join(hexvals)


class _RelaxedNamesEnum(EnumMeta):
    def __getitem__(cls, name):
        return super().__getitem__(name.upper())


class RelaxedNamesEnum(Enum, metaclass=_RelaxedNamesEnum):
    """Enum class where name lookup is case insensitive."""
    pass


def rpadlist(list, width, fillitem=0):
    """Pad `list` with `fillitem` to `width`.

    >>> rpadlist([1, 2, 3], 5)
    [1, 2, 3, 0, 0]
    >>> rpadlist([1, 2, 3], 5, fillitem=None)
    [1, 2, 3, None, None]
    """
    pad_width = width - len(list)
    list.extend([fillitem] * pad_width)
    return list


def clamp(value, clampmin, clampmax):
    """Clamp numeric `value` to interval [`clampmin`, `clampmax`]."""
    clamped = max(clampmin, min(clampmax, value))
    if clamped != value:
        _LOGGER.debug('clamped %s to interval [%s, %s]', value, clampmin, clampmax)
    return clamped


def fraction_of_byte(ratio=None, percentage=None):
    """Return `ratio` xor `percentage` expressed as a fraction of 255.

    >>> fraction_of_byte(ratio=.8)
    204
    >>> fraction_of_byte(percentage=20)
    51
    """
    if percentage is not None:
        ratio = percentage / 100
    if ratio is not None:
        if ratio < 0 or ratio > 1:
            raise ValueError('cannot express ratios outside of [0, 1]')
        return round(ratio * 255)
    raise ValueError('either ratio or percentage must not be None')


def u16le_from(buffer, offset=0):
    """Read an unsigned 16-bit little-endian integer from `buffer`.

    >>> u16le_from(b'\x45\x05\x03')
    1349
    >>> u16le_from(b'\x45\x05\x03', offset=1)
    773
    """
    return int.from_bytes(buffer[offset: offset + 2], byteorder='little')


def u16be_from(buffer, offset=0):
    """Read an unsigned 16-bit big-endian integer from `buffer`.

    >>> u16be_from(b'\x45\x05\x03')
    17669
    >>> u16be_from(b'\x45\x05\x03', offset=1)
    1283
    """
    return int.from_bytes(buffer[offset: offset + 2], byteorder='big')


def delta(profile):
    """Compute a profile's Δx and Δy."""
    return [(cur[0]-prev[0], cur[1]-prev[1])
            for cur, prev in zip(profile[1:], profile[:-1])]


def normalize_profile(profile, critx, max_value=100):
    """Normalize a [(x:int, y:int), ...] profile.

    The normalized profile will ensure that:

     - the profile is a monotonically increasing function
       (i.e. for every i, i > 1, x[i] - x[i-1] > 0 and y[i] - y[i-1] >= 0)
     - the profile is sorted
     - a (critx, 100) failsafe is enforced
     - only the first point that sets y := 100 is kept

    >>> normalize_profile([(30, 40), (25, 25), (35, 30), (40, 35), (40, 80)], 60)
    [(25, 25), (30, 40), (35, 40), (40, 80), (60, 100)]
    >>> normalize_profile([(30, 40), (25, 25), (35, 30), (40, 100)], 60)
    [(25, 25), (30, 40), (35, 40), (40, 100)]
    >>> normalize_profile([(30, 40), (25, 25), (35, 100), (40, 100)], 60)
    [(25, 25), (30, 40), (35, 100)]
    >>> normalize_profile([], 60)
    [(60, 100)]
    >>> normalize_profile([], 60, 300)
    [(60, 300)]

    """
    profile = sorted(list(profile) + [(critx, max_value)], key=lambda p: (p[0], -p[1]))
    mono = profile[0:1]
    for (x, y), (xb, yb) in zip(profile[1:], profile[:-1]):
        if x == xb:
            continue
        if y < yb:
            y = yb
        mono.append((x, y))
        if y == max_value:
            break
    return mono


def interpolate_profile(profile, x):
    """Interpolate y given x and a [(x: int, y: int), ...] profile.

    Requires the profile to be sorted by x, with no duplicate x values (see
    normalize_profile).  Expects profiles with integer x and y values, and
    returns duty rounded to the nearest integer.

    >>> interpolate_profile([(20, 50), (50, 70), (60, 100)], 33)
    59
    >>> interpolate_profile([(20, 50), (50, 70)], 19)
    50
    >>> interpolate_profile([(20, 50), (50, 70)], 51)
    70
    >>> interpolate_profile([(20, 50)], 20)
    50
    """
    lower, upper = profile[0], profile[-1]
    for step in profile:
        if step[0] <= x:
            lower = step
        if step[0] >= x:
            upper = step
            break
    if lower[0] == upper[0]:
        return lower[1]
    return round(lower[1] + (x - lower[0])/(upper[0] - lower[0])*(upper[1] - lower[1]))


def color_from_str(x):
    """Parse a color, and, if necessary, translate it into the RGB model.

    The input string can be encoded in several formats:

     - ffffff: hexadecimal RGB implicit tuple (with or without the prefix '0x')
     - rgb(255, 255, 255): explicit RGB, R,G,B ∊ [0, 255]
     - hsv(360, 100, 100): explicit HSV, H ∊ [0, 360], SV ∊ [0, 100]
     - hsl(360, 100, 100): explicit HSL, H ∊ [0, 360], SV ∊ [0, 100]

    >>> color_from_str('fF7f3f')
    [255, 127, 63]
    >>> color_from_str('0xfF7f3f')
    [255, 127, 63]
    >>> color_from_str('0XfF7f3f')
    [255, 127, 63]
    >>> color_from_str('#fF7f3f')
    [255, 127, 63]
    >>> color_from_str('Rgb(255, 127, 63)')
    [255, 127, 63]
    >>> color_from_str('Hsv(20, 75, 100)')
    [255, 128, 64]
    >>> color_from_str('Hsl(20, 100, 62)')
    [255, 126, 61]

    >>> color_from_str('fF7f3f1f')
    Traceback (most recent call last):
        ...
    ValueError: cannot parse color: fF7f3f1f
    >>> color_from_str('0bff00ff')
    Traceback (most recent call last):
        ...
    ValueError: cannot parse color: 0bff00ff
    >>> color_from_str('rgb()')
    Traceback (most recent call last):
        ...
    ValueError: expected 3-element triple: rgb()
    >>> color_from_str('rgb(255)')
    Traceback (most recent call last):
        ...
    ValueError: expected 3-element triple: rgb(255)
    >>> color_from_str('rgb(300, 255, 255)')
    Traceback (most recent call last):
        ...
    ValueError: expected value in range [0, 255]: 300 in rgb(300, 255, 255)
    >>> color_from_str('hsv(360, 150, 100)')
    Traceback (most recent call last):
        ...
    ValueError: expected value in range [0, 100]: 150 in hsv(360, 150, 100)
    >>> color_from_str('hsl(360, 100, 150)')
    Traceback (most recent call last):
        ...
    ValueError: expected value in range [0, 100]: 150 in hsl(360, 100, 150)
    """

    def parse_triple(sub, maxvalues):
        literal = literal_eval(sub)
        if not isinstance(literal, tuple) or len(literal) != 3:
            raise ValueError(f'expected 3-element triple: {x}')
        for value, maxvalue in zip(literal, maxvalues):
            if not isinstance(value, int) and not isinstance(value, float):
                raise ValueError(f'expected float or int: {value} in {x}')
            if value < 0 or value > maxvalue:
                raise ValueError(f'expected value in range [0, {maxvalue}]: {value} in {x}')
        return literal

    xl = x.lower()

    if xl.startswith('rgb('):
        r, g, b = parse_triple(x[3:], (255, 255, 255))
        return [r, g, b]
    elif xl.startswith('hsv('):
        h, s, v = parse_triple(x[3:], (360, 100, 100))
        return list(map(lambda b: round(b*255), colorsys.hsv_to_rgb(h/360, s/100, v/100)))
    elif xl.startswith('hsl('):
        h, s, l = parse_triple(x[3:], (360, 100, 100))
        return list(map(lambda b: round(b*255), colorsys.hls_to_rgb(h/360, l/100, s/100)))
    elif len(x) == 6:
        return list(bytes.fromhex(x))
    elif len(x) == 7 and x.startswith('#'):
        return list(bytes.fromhex(x[1:]))
    elif len(x) == 8 and xl.startswith('0x'):
        return list(bytes.fromhex(x[2:]))
    else:
        raise ValueError(f'cannot parse color: {x}')


def check_unsafe(*reqs, unsafe=None, error=False, **kwargs):
    """Check if unsafe feature requirements are met.

    Unstable.

    Checks if the requirements in the positional arguments (`*reqs`) are all
    met by the `unsafe` string list of enabled features.

    >>> check_unsafe('foo', unsafe='foo,bar')
    True
    >>> check_unsafe('foo', 'bar', unsafe='foo,bar')
    True
    >>> check_unsafe('foo', unsafe=None)
    False
    >>> check_unsafe('foo', 'baz', unsafe='foo,bar')
    False

    If `error=True` and some requirements have not been met, raises
    `liquidctl.error.UnsafeFeaturesNotEnabled`.  In the default `error=False`
    mode, a boolean is return indicating whether all requirements were met.

    >>> check_unsafe('foo', 'baz', unsafe='foo,bar', error=True)
    Traceback (most recent call last):
        ...
    liquidctl.error.UnsafeFeaturesNotEnabled: required unsafe features have not been enabled: baz

    In driver code, `unsafe` is normally passed in `**kwargs`.

    >>> kwargs = {'unsafe': 'foo,bar'}
    >>> check_unsafe('foo', 'bar', **kwargs)
    True
    >>> check_unsafe('foo', 'baz', error=True, **kwargs)
    Traceback (most recent call last):
        ...
    liquidctl.error.UnsafeFeaturesNotEnabled: required unsafe features have not been enabled: baz
    """

    if unsafe:
        reqs = tuple(filter(lambda x: x not in unsafe, reqs))

    if not reqs:
        return True

    if error:
        raise UnsafeFeaturesNotEnabled(reqs)
    return False


def map_direction(direction, forward=None, backward=None):
    """Check a `direction` option and run the appropriate closure.

    Unstable.

    Accepts both US and UK spellings.  Raises a `ValueError` if the option
    value is neither forward[s] nor backward[s].

    >>> map_direction('forward', 3, 42)
    3
    >>> map_direction('forwards', 3, 42)
    3
    >>> map_direction('backward', 3, 42)
    42
    >>> map_direction('backwards', 3, 42)
    42
    >>> map_direction('fooowwd', 3, 42)
    Traceback (most recent call last):
        ...
    ValueError: invalid direction: 'fooowwd'
    """

    if 'forwards'.startswith(direction):
        return forward
    elif 'backwards'.startswith(direction):
        return backward
    else:
        raise ValueError(f'invalid direction: {direction!r}')


def fan_mode_parser(value: Optional[str], max_fans: Optional[int] = None) -> dict:
    """Convert the --fan-mode=<key>:<value>[,...] options into a {key: value, ....} dictionary.
    The default is an empty dictionary.

    Unstable.

    >>> fan_mode_parser(None, 5)
    {}

    >>> fan_mode_parser('', 5)
    {}

    >>> fan_mode_parser('1:dc', 5)
    {'1': 'dc'}

    >>> fan_mode_parser('2:auto', 5)
    {'2': 'auto'}

    >>> fan_mode_parser('3:off', 5)
    {'3': 'off'}

    >>> fan_mode_parser('1:DC', 5)
    {'1': 'dc'}

    >>> fan_mode_parser('2:AUTO', 5)
    {'2': 'auto'}

    >>> fan_mode_parser('3:OFF', 5)
    {'3': 'off'}

    >>> fan_mode_parser('5:OFF', 5)
    {'5': 'off'}

    >>> fan_mode_parser('5:OFF')
    {'5': 'off'}

    >>> fan_mode_parser('1:dc,2:auto,3:off,4:pwm', 5)
    {'1': 'dc', '2': 'auto', '3': 'off', '4': 'pwm'}

    >>> fan_mode_parser('1:dc, 2:auto, 3:off', 5)
    {'1': 'dc', '2': 'auto', '3': 'off'}

    >>> fan_mode_parser('4:dc, 3:auto, 2:off', 5)
    {'2': 'off', '3': 'auto', '4': 'dc'}

    >>> fan_mode_parser('1 :dc, 2: auto, 3 : off,    4       :     auto   ', 5)
    {'1': 'dc', '2': 'auto', '3': 'off', '4': 'auto'}

    >>> fan_mode_parser('1:dc:dc', 5)
    Traceback (most recent call last):
        ...
    ValueError: invalid format, should be '<fan num>:<mode>'

    >>> fan_mode_parser('-1:dc', 5)
    Traceback (most recent call last):
        ...
    ValueError: invalid fan number: '-1'

    >>> fan_mode_parser('0:pwm', 5)
    Traceback (most recent call last):
        ...
    ValueError: invalid fan number: '0'

    >>> fan_mode_parser('5:dc', 4)
    Traceback (most recent call last):
        ...
    ValueError: invalid fan number: '5'

    >>> fan_mode_parser('a:dc', 5)
    Traceback (most recent call last):
        ...
    ValueError: invalid fan number: 'a'


    >>> fan_mode_parser('1:PMW', 5)
    Traceback (most recent call last):
        ...
    ValueError: invalid fan mode: 'PMW'

    """

    if not value:
        return {}

    parts = value.split(',')

    opts = {}
    for p in parts:
        p2 = p.split(':')
        if len(p2) != 2:
            raise ValueError("invalid format, should be '<fan num>:<mode>'")

        [key, val] = [i.strip() for i in p2]

        try:
            key_val = int(key, 10)
        except ValueError:
            raise ValueError(f"invalid fan number: '{key}'")

        if key_val <= 0 or (max_fans is not None and key_val > max_fans):
            raise ValueError(f"invalid fan number: '{key}'")

        if val.lower() not in ['off', 'auto', 'dc', 'pwm']:
            raise ValueError(f"invalid fan mode: '{val}'")

        opts.update({key: val.lower()})


    return dict(sorted(opts.items(), key=lambda item: item[0]))


@lru_cache(maxsize=None)
def mkCrcFun(crc_name):
    """Efficiently construct a predefined CRC function.

    Unstable.

    For the available algorithms, see
    <http://crcmod.sourceforge.net/crcmod.predefined.html#predefined-crc-algorithms>.

    This function implements memoization, only constructing each requested CRC
    algorithm implementation once.
    """

    return crcmod.predefined.mkCrcFun(crc_name)
