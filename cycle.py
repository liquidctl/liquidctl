#!/usr/bin/env python

import liquidctl.cli as lc
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

sys.argv[1:] = ["set", "led6", "color", "color-cycle", "--speed", "slower"]

STEPS = 30
sys.argv[1:] = ["--debug"] if args.debug else []
sys.argv += "set led6 color fixed ff0000".split()
lc.main()
lookup = []

for i in range(len(colors) - 1):
    gradient = colors[i].interpolate(colors[i + 1], space=args.space)
    lookup += [gradient(x / STEPS).to_string(hex=True) for x in range(STEPS)]


lookup += reversed(lookup)
print(lookup)
while True:
    for x in range(2 * STEPS):
        c = lookup[x]
        # keeping these hook variables in the liquidctl.cli module lets us
        # call back into _device_set_color() with minimal overhead
        lc.hook_args["<color>"] = [c[1:]]
        with lc.hook_dev.connect(**lc.hook_opts):
            lc._device_set_color(lc.hook_dev, lc.hook_args, **lc.hook_opts)
        time.sleep(0.25 / STEPS)
