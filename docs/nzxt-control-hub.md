# NZXT Control Hub

The NZXT Control Hub is a fan controller that ships with newer NZXT cases (2024+), such as the H9 Flow. It provides five independent fan channels with standard 4-pin connectors, supporting both PWM and DC control.

## Device Info

- **Vendor ID:** 0x1e71
- **Product ID:** 0x2022
- **USB Interface:** HID (512-byte reports)

## Features

- 5 independent fan channels (fan1-fan5)
- PWM and DC fan control (auto-detected)
- Fan duty reporting (0-100%)

## Initialization

The device should be initialized after boot or after waking from sleep:

```shell
liquidctl initialize --match "Control Hub"
```

## Retrieving Status

```shell
$ liquidctl status --match "Control Hub"
NZXT Control Hub
├── Fan 1 control mode    Auto
├── Fan 1 duty              50  %
├── Fan 2 control mode    Auto
├── Fan 2 duty               0  %
├── Fan 3 control mode    Auto
├── Fan 3 duty               0  %
├── Fan 4 control mode    Auto
├── Fan 4 duty              50  %
├── Fan 5 control mode    Auto
└── Fan 5 duty              50  %
```

## Controlling Fan Speeds

Set all fans to the same speed:

```shell
liquidctl set sync speed 50 --match "Control Hub"
```

Set individual fan channels:

```shell
liquidctl set fan1 speed 40 --match "Control Hub"
liquidctl set fan4 speed 75 --match "Control Hub"
```

## Channel Mapping

The physical fan connected to each channel depends on how the case is wired. For reference, a typical NZXT H9 Flow configuration:

| Channel | Typical Connection |
|---------|-------------------|
| fan1 | Bottom intake fans |
| fan2 | (varies) |
| fan3 | (varies) |
| fan4 | Front/GPU radiator fans |
| fan5 | Rear exhaust fan |

Check your case documentation or test each channel individually to determine your specific mapping.

## Temperature-Based Control

The Control Hub does not have built-in temperature sensors or fan curve support. For automatic temperature-based control, use an external script or daemon that monitors system temperatures and adjusts fan speeds accordingly.

Example using a simple bash loop:

```bash
#!/bin/bash
while true; do
    GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits)
    if [ "$GPU_TEMP" -gt 70 ]; then
        liquidctl set fan4 speed 100 --match "Control Hub"
    elif [ "$GPU_TEMP" -gt 60 ]; then
        liquidctl set fan4 speed 75 --match "Control Hub"
    elif [ "$GPU_TEMP" -gt 50 ]; then
        liquidctl set fan4 speed 50 --match "Control Hub"
    else
        liquidctl set fan4 speed 35 --match "Control Hub"
    fi
    sleep 3
done
```

## Limitations

- **LED Control:** Not yet implemented. The Control Hub's LED protocol differs from other NZXT devices and requires further reverse engineering.
- **RPM Reporting:** The protocol locations for RPM data have been identified but not yet fully verified.
- **Fan Curves:** The device does not support uploading fan curves; temperature-based control must be handled externally.

## Protocol Notes

The Control Hub uses a protocol similar to the Smart Device V2 but with larger HID reports:

- **Packet Size:** 512 bytes (vs 64 bytes for Smart Device V2)
- **Fan Channels:** 5 (vs 3 for Smart Device V2)
- **Init Command:** `[0x60, 0x03]`
- **Fan Speed Command:** `[0x62, 0x01, channel_mask, duty0, duty1, duty2, duty3, duty4]`
- **Status Message:** Prefix `0x67 0x02`, duties at offset 40-44
