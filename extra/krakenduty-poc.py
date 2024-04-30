#!/usr/bin/env python3

"""krakenduty proof of concept – translate Kraken X speeds to duty values

This is just a proof of concept.

Usage:
  krakenduty-poc train
  krakenduty-poc status
  krakenduty-poc --help
  krakenduty-poc --version

Copyright Jonas Malaco and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import ast
from time import sleep

from docopt import docopt
from liquidctl.driver.kraken_two import KrakenTwoDriver
from liquidctl.util import interpolate_profile as interpolate

DATAFILE = ".krakenduty-poc"
DUTY_STEP = 5
DUTY_SLEEP = 5
DUTY_SAMPLES = 5


def get_speeds(device):
    status = {k: v for k, v, u in device.get_status()}
    return (status["Fan speed"], status["Pump speed"])


def find_duty_values(training_data, fan_speed, pump_speed):
    # for now simply interpolate, but this is terrible because it ignores variance
    fan_duty = interpolate(sorted([(speed, duty) for duty, speed, _ in training_data]), fan_speed)
    pump_duty = interpolate(sorted([(speed, duty) for duty, _, speed in training_data]), pump_speed)
    # don't return values outside the allowed bounds to avoid confusion
    return (min(max(fan_duty, 25), 100), min(max(pump_duty, 50), 100))


def do_train(device):
    # read current values
    fan_speed, pump_speed = get_speeds(device)
    print("starting values: fan = {} rpm, pump = {} rpm".format(fan_speed, pump_speed))

    # train
    training_data = []
    for duty in range(0, 101, DUTY_STEP):
        # don't worry if duty is off spec, the driver will correct it
        for channel in ["fan", "pump"]:
            device.set_fixed_speed(channel, duty)
        # wait significantly to allow the speed to stabilize
        sleep(DUTY_SLEEP)
        # get a few samples because there is some natural variation;
        # though this might need some delays and, also, depend on the actually
        # observed variance
        samples = [get_speeds(device) for i in range(DUTY_SAMPLES)]
        average = [sum(i) / len(i) for i in zip(*samples)]
        print("{}% duty: fan = {:.0f} rpm, pump = {:.0f} rpm".format(duty, *average))
        training_data.append([duty] + average)
        with open(DATAFILE, "w") as f:
            f.write(str(training_data))

    # (try to) restore the current values
    fan_duty, pump_duty = find_duty_values(training_data, fan_speed, pump_speed)
    print("applying fixed values: fan = {}%, pump = {}%".format(fan_duty, pump_duty))
    device.set_fixed_speed("fan", fan_duty)
    device.set_fixed_speed("pump", pump_duty)


def do_status(device):
    # read training data
    training_data = []
    with open(DATAFILE, "r") as f:
        training_data = ast.literal_eval(f.read())

    # augment
    status = []
    for k, v, u in device.get_status():
        status.append((k, v, u))
        if k == "Fan speed":
            fan_duty, _ = find_duty_values(training_data, v, 0)
            status.append(("Fan duty", fan_duty, "%"))
        elif k == "Pump speed":
            _, pump_duty = find_duty_values(training_data, 0, v)
            status.append(("Pump duty", pump_duty, "%"))

    # report
    print("{}".format(device.description))
    for k, v, u in status:
        print("{:<20}  {:>6}  {:<3}".format(k, v, u))
    print("")


if __name__ == "__main__":
    args = docopt(__doc__, version="0.0.2")

    device = KrakenTwoDriver.find_supported_devices()[0]
    device.connect()
    try:
        if args["train"]:
            do_train(device)
        elif args["status"]:
            do_status(device)
        else:
            raise Exception("nothing to do")
    finally:
        device.disconnect()
