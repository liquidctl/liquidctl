#!/usr/bin/env python
# Copyright (C) 2022–2022  Peter Eckersley <pde@pde.is>
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import sys
import time

import liquidctl.cli as lc
import liquidctl


try:
    import coloraide as c
except ImportError:
    print("The python coloraide package is not installed...")
    print("Try installing it with: pip install coloraide")
    sys.exit(1)


teal = c.Color("#2de544")
bluer = c.Color("#2d8a8d")
deep_blue = c.Color("#001030")
purple = c.Color("#c000c0")
red = c.Color("#d00000")

# set up argparse
parser = argparse.ArgumentParser(
    description="Cycle through colors on an Gigabyte RGB Fusion 2.0 device."
)
parser.add_argument(
    "--space",
    type=str,
    default="srgb",
    help="Color space to use; see https://facelessuser.github.io/coloraide/colors/",
)
# you can provide 0 or more colors to cycle through
parser.add_argument("colors", nargs="*", help="Colors to cycle through")
parser.add_argument(
    "--steps", default=30, type=int, help="Number of steps per color fade (default: 30)"
)
parser.add_argument("--debug", action="store_true", help="Print debug messages")
parser.add_argument(
    "--channel",
    type=str,
    default="led6",
    help="Channel to use; see https://github.com/liquidctl/liquidctl/blob/main/docs/gigabyte-rgb-fusion2-guide.md",
)
parser.add_argument(
    "--speed", type=float, default=1.0, help="Speed (seconds per color transition)"
)

args = parser.parse_args()

colors = [c.Color("#" + x) for x in args.colors]
if len(colors) < 2:
    colors.append(teal)
if len(colors) < 2:
    colors.append(bluer)

devs = liquidctl.driver.rgb_fusion2.RgbFusion2.find_supported_devices()
if not devs:
    print("No Gigabyte RGB Fusion 2.0 device found.")
    sys.exit(1)
elif len(devs) > 1:
    print("Multiple Gigabyte RGB Fusion 2.0 devices found, using first one.")

dev = devs[0]

lookup = []


def to_int(color):
    string = color.to_string()  # "rgb(255 75 0)"
    string = string.partition("(")[2][:-1]  # "255 75 0"
    string = string.split()  # ["255", "75", "0"]
    return [int(float(x)) for x in string]


colors.append(colors[0])  # add first color at the end, so we can loop

for i in range(len(colors) - 1):
    gradient = colors[i].interpolate(colors[i + 1], space=args.space)
    cols = [to_int(gradient(x / args.steps)) for x in range(args.steps)]
    lookup += cols

if args.debug:
    print("Cycling through", len(lookup), "colors:\n", lookup)


while True:
    # reconnect occasionally, just in case these connections die and we can bring them back
    with dev.connect():
        for c in lookup:
            dev.set_color(channel=args.channel, mode="fixed", colors=[c])
            time.sleep(args.speed * 2.0 / args.steps)
