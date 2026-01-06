#!/usr/bin/env python3

"""yoda – dynamically adjust liquidctl device pump and fan speeds.

Periodically adjusts pump and fan speeds according to user-specified profiles.

Different sensors can be used for each channel.  Use show-sensors to view the
sensors available for use with a particular device.

To avoid jerks in pump or fan speeds, an exponential moving average is used as
low-pass filter on sensor data.

Profiles are specified as comma-separated lists of `(temperature,duty)` pairs.
For example: `(20,50),(40,65),(40,65),(50,100)` specifies a duty of 65% at
40°C.  The profile will be linearly interpolated between the specified points.

In device controlled mode, sets the device internal control profile and periodically
sends sensor data, but the device will independently control duty cycles to match the temperature.
Named profiles implemented by the device manufacturer, such as "silent", "game", "smart",
are only available in device controlled mode.

Escape sequences or appropriate single or double quotes should be employed to
escape characters that are reserved by the shell in use (e.g. in the case of
bash, the parenthesis and any optional whitespace).  In practice, wrapping the
profile in double quotes should be sufficient for most users.

Examples:
  yoda --match grid show-sensors
  yoda --match grid control fan1 with "(20,20),(35,100)" on nct6793.systin
  yoda --match kraken show-sensors
  yoda --match kraken control pump with "(20,50),(50,100)" on istats.cpu and fan with "(20,25),(34,100)" on _internal.liquid
  yoda --match msi control pump with "smart" on coretemp.package_id_0 and fans with "silent" on coretemp.package_id_0

Usage:
  yoda [options] show-sensors
  yoda [options] control (<channel> with <profile> on <sensor> [and])...
  yoda --help
  yoda --version

Options:
  --interval <seconds>     Update interval in seconds [default: 2]
  -m, --match <substring>  Filter devices by description substring
  -n, --pick <number>      Pick among many results for a given filter
  --vendor <id>            Filter devices by vendor id
  --product <id>           Filter devices by product id
  --release <number>       Filter devices by release number
  --serial <number>        Filter devices by serial number
  --bus <bus>              Filter devices by bus
  --address <address>      Filter devices by address in bus
  --usb-port <port>        Filter devices by USB port in bus
  --unsafe <features>      Comma-separated bleeding-edge features to enable
  -v, --verbose            Output additional information
  -g, --debug              Show debug information on stderr
  --legacy-690lc           Use Asetek 690LC in legacy mode (old Krakens)
  --use-device-controller  Use the control loop integrated to the device (MPG coreliquid device)
  --version                Display the version number
  --help                   Show this message

Requirements:
  all platforms  liquidctl, including the Python APIs (pip install liquidctl)
  Linux/FreeBSD  psutil [optional] (pip install psutil)
  macOS          iStats (gem install iStats)
  Windows        none, system sensors not yet supported

Changelog:
  0.0.6  Add --use-device-controller and make psutil optional.
  0.0.5  Document how profiles are specified
  0.0.4  Fix casing of log and error messages
  0.0.3  Remove duplicate option definition
  0.0.2  Add low-pass filter and basic error handling.
  0.0.1  Generalization of krakencurve-poc 0.0.2 to multiple devices.

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""


import ast
import logging
import math
import sys
import time
from datetime import datetime

from docopt import docopt
import liquidctl.cli as _borrow
from liquidctl.util import normalize_profile, interpolate_profile
import liquidctl.driver

VERSION = "0.0.6"

LOGGER = logging.getLogger(__name__)

INTERNAL_CHIP_NAME = "_internal"

MAX_FAILURES = 3

if sys.platform == "darwin":
    import re
    import subprocess
elif sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):
    try:
        import psutil
    except ModuleNotFoundError:
        psutil = None


devices_sensors = None


def read_sensors(device, sensors_to_read, **kwargs):
    global devices_sensors
    if not devices_sensors:
        devices_sensors = {}
    sensors = {}
    # Only read device sensors when required
    if device in devices_sensors and sensors_to_read in devices_sensors[device]:
        for k, v, u in device.get_status(**kwargs):
            if u == "°C":
                sensor_name = k.lower().replace(" ", "_").replace("_temperature", "")
                sensors[f"{INTERNAL_CHIP_NAME}.{sensor_name}"] = v
        devices_sensors[device] = sensors
    if sys.platform == "darwin":
        istats_stdout = subprocess.check_output(["istats"]).decode("utf-8")
        for line in istats_stdout.split("\n"):
            if line.startswith("CPU"):
                cpu_temp = float(re.search(r"\d+\.\d+", line).group(0))
                sensors["istats.cpu"] = cpu_temp
                break
    elif psutil:
        for m, li in psutil.sensors_temperatures().items():
            for label, current, _, _ in li:
                sensor_name = label.lower().replace(" ", "_")
                sensors[f"{m}.{sensor_name}"] = current
        sensors["cpu_freq"] = psutil.cpu_freq().current
    return sensors


def show_sensors(device, **kwargs):
    print("{:<60}  {:>14}".format("Sensor identifier", "Value"))
    print("-" * 80)
    sensors = read_sensors(device, **kwargs)
    for k, v in sensors.items():
        unit = "MHz" if k == "cpu_freq" else "°C"
        print(f"{k:<60}  {v:>14.1f} {unit}")


def parse_profile(arg, mintemp=0, maxtemp=100, minduty=0, maxduty=100, str_allowed=False):
    """Parse, validate and normalize a temperature–duty profile.

    >>> parse_profile('smart', str_allowed=True)
    'smart'

    >>> parse_profile('(20,30),(30,50),(34,80),(40,90)', 0, 60, 25, 100)
    [(20, 30), (30, 50), (34, 80), (40, 90), (60, 100)]
    >>> parse_profile('35', 0, 60, 25, 100)
    [(0, 35), (59, 35), (60, 100)]

    The profile is validated in structure and acceptable ranges.  Duty is
    checked against `minduty` and `maxduty`.  Temperature must be between
    `mintemp` and `maxtemp`.

    >>> parse_profile('(20,30),(50,100', 0, 60, 25, 100)
    Traceback (most recent call last):
        ...
    ValueError: profile must be comma-separated (temperature, duty) tuples or supported mode name
    >>> parse_profile('(20,30),(50,100,2)', 0, 60, 25, 100)
    Traceback (most recent call last):
        ...
    ValueError: profile must be comma-separated (temperature, duty) tuples
    >>> parse_profile('(20,30),(50,97.6)', 0, 60, 25, 100)
    Traceback (most recent call last):
        ...
    ValueError: duty must be integer between 25 and 100
    >>> parse_profile('(20,15),(50,100)', 0, 60, 25, 100)
    Traceback (most recent call last):
        ...
    ValueError: duty must be integer between 25 and 100
    >>> parse_profile('(20,30),(70,100)', 0, 60, 25, 100)
    Traceback (most recent call last):
        ...
    ValueError: temperature must be integer between 0 and 60

    """
    try:
        if str_allowed and arg in liquidctl.driver.msi.MpgCooler.BUILTIN_MODES:
            return arg
        else:
            val = ast.literal_eval("[" + arg + "]")
            if len(val) == 1 and isinstance(val[0], int):
                # for arg == '<number>' set fixed duty between mintemp and maxtemp - 1
                val = [(mintemp, val[0]), (maxtemp - 1, val[0])]
    except:
        raise ValueError(
            "profile must be comma-separated (temperature, duty) tuples or supported mode name"
        )
    for step in val:
        if not isinstance(step, tuple) or len(step) != 2:
            raise ValueError("profile must be comma-separated (temperature, duty) tuples")
        temp, duty = step
        if not isinstance(temp, int) or temp < mintemp or temp > maxtemp:
            raise ValueError(
                "temperature must be integer between {} and {}".format(mintemp, maxtemp)
            )
        if not isinstance(duty, int) or duty < minduty or duty > maxduty:
            raise ValueError("duty must be integer between {} and {}".format(minduty, maxduty))
    return normalize_profile(val, critx=maxtemp)


def auto_control(device, channels, profiles, sensors, update_interval, **kwargs):
    """Communicate sensor data directly with the device.

    Implemented for use with the MSI coreliquid AIO.
    Allows compatible devices to utilize their internal control loop
    to determine appropriate fan speeds for the CPU temperature.
    """
    assert getattr(
        device, "HAS_AUTOCONTROL", False
    ), f"No registered control loop capability for device {device}!"

    device.set_profiles(channels, profiles, **kwargs)

    assert all(
        s == sensors[0] for s in sensors
    ), "Controlling different channels with different sensors not possible with device control"
    sensor = sensors[0]

    LOGGER.info("starting...")
    failures = 0
    while True:
        try:
            sensor_data = read_sensors(device, **kwargs)
            temp = sensor_data[sensor]
            freq = sensor_data.get("cpu_freq", 0)

            device.set_time(datetime.now(), **kwargs)
            device.set_hardware_status(
                temp,
                cpu_f=freq,
                gpu_f=sensor_data.get("gpu_freq", 0),
                gpu_U=sensor_data.get("gpu_usage", 0),
                **kwargs,
            )
            failures = 0
        except Exception as err:
            failures += 1
            LOGGER.error(err)
            if failures >= MAX_FAILURES:
                LOGGER.critical("too many failures in a row: %d", failures)
                raise
        time.sleep(update_interval)


def control(device, channels, profiles, sensors, update_interval, **kwargs):
    LOGGER.info(
        "device: %s on bus %s and address %s", device.description, device.bus, device.address
    )
    for channel, profile, sensor in zip(channels, profiles, sensors):
        LOGGER.info("channel: %s following profile %s on %s", channel, str(profile), sensor)

    averages = [None] * len(channels)
    cutoff_freq = 1 / update_interval / 10
    alpha = 1 - math.exp(-2 * math.pi * cutoff_freq)
    LOGGER.info(
        "update interval: %d s; cutoff frequency (low-pass): %.2f Hz; ema alpha: %.2f",
        update_interval,
        cutoff_freq,
        alpha,
    )

    try:
        # more efficient and safer API, but only supported by very few devices
        apply_duty = device.set_instantaneous_speed
    except AttributeError:
        apply_duty = device.set_fixed_speed

    LOGGER.info("starting...")
    failures = 0
    last_duty = {}
    while True:
        try:
            sensor_data = read_sensors(device, sensors, **kwargs)
            for i, (channel, profile, sensor) in enumerate(zip(channels, profiles, sensors)):
                # compute the exponential moving average (ema), used as a low-pass filter (lpf)
                ema = averages[i]
                sample = sensor_data[sensor]
                if ema is None:
                    ema = sample
                else:
                    ema = alpha * sample + (1 - alpha) * ema
                averages[i] = ema

                # interpolate on sensor ema and apply corresponding duty
                duty = interpolate_profile(profile, ema)
                LOGGER.info(
                    "%s control: lpf(%s) = lpf(%.1f°C) = %.1f°C => duty := %d%%",
                    channel,
                    sensor,
                    sample,
                    ema,
                    duty,
                )
                if channel not in last_duty:
                    last_duty[channel] = duty
                # Only reapply duty when duty changed
                if last_duty[channel] == duty:
                    continue
                apply_duty(channel, duty, **kwargs)
                last_duty[channel] = duty
            if getattr(device, "NEEDS_TIME", False):
                device.set_time(datetime.now(), **kwargs)
            if getattr(device, "NEEDS_HWSTATUS", False):
                device.set_hardware_status(
                    sensor_data[sensors[0]],
                    cpu_f=sensor_data.get("cpu_freq", 0),
                    gpu_f=sensor_data.get("gpu_freq", 0),
                    gpu_U=sensor_data.get("gpu_usage", 0),
                    **kwargs,
                )

            failures = 0
        except Exception as err:
            failures += 1
            LOGGER.error(err)
            if failures >= MAX_FAILURES:
                LOGGER.critical("too many failures in a row: %d", failures)
                raise
        time.sleep(update_interval)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "doctest":
        import doctest

        doctest.testmod(verbose=True)
        sys.exit(0)

    args = docopt(__doc__, version="yoda v{}".format(VERSION))

    if args["--debug"]:
        args["--verbose"] = True
        logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(name)s: %(message)s")
        import liquidctl.version

        LOGGER.debug("yoda v%s", VERSION)
        LOGGER.debug("liquidctl v%s", liquidctl.version.__version__)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
        LOGGER.setLevel(logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
        sys.tracebacklimit = 0
    if args["--unsafe"] is not None:
        unsafe = args["--unsafe"].lower().split(",")
    else:
        unsafe = []

    if (sys.platform.startswith("linux") or sys.platform.startswith("freebsd")) and not psutil:
        LOGGER.warning("system sensors are not available, psutil not found")

    frwd = _borrow._make_opts(args)
    selected = list(liquidctl.driver.find_liquidctl_devices(**frwd))
    if len(selected) > 1:
        raise SystemExit(
            "too many devices, filter or select one.  See liquidctl --help and yoda --help."
        )
    elif len(selected) == 0:
        raise SystemExit("no devices matches available drivers and selection criteria")

    device = selected[0]
    device.connect(unsafe=unsafe)
    try:
        if args["show-sensors"]:
            show_sensors(device, unsafe=unsafe)
        elif args["control"]:
            if args["--use-device-controller"]:
                auto_control(
                    device,
                    args["<channel>"],
                    list(map(lambda p: parse_profile(p, str_allowed=True), args["<profile>"])),
                    args["<sensor>"],
                    update_interval=int(args["--interval"]),
                    unsafe=unsafe,
                )
            else:
                control(
                    device,
                    args["<channel>"],
                    list(map(parse_profile, args["<profile>"])),
                    args["<sensor>"],
                    update_interval=int(args["--interval"]),
                    unsafe=unsafe,
                )
        else:
            raise Exception("nothing to do")
    except KeyboardInterrupt:
        LOGGER.info("stopped by user.")
    finally:
        device.disconnect()
