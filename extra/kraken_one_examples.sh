#!/bin/bash -xe

DEVICE="--vendor 0x2433 --product 0xb200 --legacy-690lc"

liquidctl $DEVICE $EXTRAOPTIONS initialize
sleep 2
liquidctl $DEVICE $EXTRAOPTIONS status


liquidctl $DEVICE $EXTRAOPTIONS set fan speed 0
liquidctl $DEVICE $EXTRAOPTIONS set pump speed 100
sleep 2
liquidctl $DEVICE $EXTRAOPTIONS status

liquidctl $DEVICE $EXTRAOPTIONS set fan speed 100
liquidctl $DEVICE $EXTRAOPTIONS set pump speed 50
sleep 2
liquidctl $DEVICE $EXTRAOPTIONS status

liquidctl $DEVICE $EXTRAOPTIONS set fan speed 50
liquidctl $DEVICE $EXTRAOPTIONS set pump speed 75
sleep 2
liquidctl $DEVICE $EXTRAOPTIONS status


liquidctl $DEVICE $EXTRAOPTIONS set led color fading ff8000 00ff80
sleep 4

liquidctl $DEVICE $EXTRAOPTIONS set led color fading ff8000 00ff80 --time-per-color 2
sleep 4

liquidctl $DEVICE $EXTRAOPTIONS set led color blinking 8000ff
sleep 6

liquidctl $DEVICE $EXTRAOPTIONS set led color blinking 8000ff --time-off 2
sleep 6

liquidctl $DEVICE $EXTRAOPTIONS set led color blinking 8000ff --time-per-color 2
sleep 6

liquidctl $DEVICE $EXTRAOPTIONS set led color blinking 8000ff --time-per-color 2 --time-off 1
sleep 6

liquidctl $DEVICE $EXTRAOPTIONS set led color fixed 00ff00
sleep 2

liquidctl $DEVICE $EXTRAOPTIONS set led color blackout
sleep 2

liquidctl $DEVICE $EXTRAOPTIONS status
