#!/usr/bin/env python

import liquidctl.cli as lc
import liquidctl
import coloraide as c
import argparse

import time
import sys

teal = c.Color("#2de544")
# bluer = c.Color("#2dca7d")
bluer = c.Color("#2d8a8d")
deep_blue = c.Color("#001030")
purple = c.Color("#c000c0")
red = c.Color("#d00000")

# set up argparse
parser = argparse.ArgumentParser(description="Cycle through colors on an Gigabyte RGB Fusion 2.0 device.")
parser.add_argument("--space", type=str, default="srgb", help="Color space to use; see https://facelessuser.github.io/coloraide/colors/")
# you can provide 0 or more colors to cycle through
parser.add_argument("colors", nargs="*", help="Colors to cycle through")
parser.add_argument("--debug", action="store_true", help="Print debug messages")
parser.add_argument("--channel", type=str, default="led6", help="Channel to use; see https://github.com/liquidctl/liquidctl/blob/main/docs/gigabyte-rgb-fusion2-guide.md")

args = parser.parse_args()

colors = [c.Color("#" + x) for x in args.colors]
if len(colors) < 2:
    colors.append(teal)
if len(colors) < 2:
    colors.append(bluer)

devs = liquidctl.find_liquidctl_devices()
for dev in devs:
    if "Gigabyte RGB Fusion 2.0" in dev.description:
        break
else:
    print("No Gigabyte RGB Fusion 2.0 device found.")
    sys.exit(1)

STEPS = 30

lookup = []

def to_int(color):
    string = color.to_string() # "rgb(255 75 0)"
    string = string.partition("(")[2][:-1] # "255 75 0"
    string = string.split() # ["255", "75", "0"]
    return [int(float(x)) for x in string]

for i in range(len(colors) - 1):
    gradient = colors[i].interpolate(colors[i + 1], space=args.space)
    cols= [to_int(gradient(x / STEPS)) for x in range(STEPS)]
    lookup += cols


lookup += reversed(lookup)
if args.debug:
    print("Cycling through", lookup)
while True:
    for x in range(2 * STEPS):
        c = lookup[x]
        with dev.connect():
            dev.set_color(channel=args.channel, mode='fixed', colors=[c])
        time.sleep(2.0 / STEPS)
