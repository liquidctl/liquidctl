---
name: Support for a new device
about: Request support for a device not currently supported
title: <Brand name> <model name>
labels: new device
---

Briefly describe the device (e.g. AIO liquid cooler).

Please also mention the first-party software that is used with it (e.g. Corsair iCue), as well as any other commonly used tools.

<!-- Bellow you find some check lists.  To check an item, fill the brackets with the letter x.  The result should look like `[x]`. -->

The device appears to support the following features:

 - [ ] monitoring of temperatures or other environment sensors
 - [ ] monitoring of fan or pump speeds or duty cycles
 - [ ] monitoring of voltages, currents or power
 - [ ] configurable fan or pump speeds
 - [ ] configurable voltages or current/power limits
 - [ ] configurable lighting of embedded LEDs
 - [ ] configurable lighting of accessories like RGB fans or LED strips

The device is connected to the host system using:

- [ ] USB
- [ ] PCI-E
- [ ] onboard (the motherboard)
- [ ] other (please elaborate)
- [ ] unknown

The device communicates with the host system using:

- [ ] HID
- [ ] USB
- [ ] I²C or SMBus
- [ ] other (please elaborate)
- [ ] unknown

Please also include any useful additional information, such as USB vendor and product IDs, the output of `lsusb -v` (Linux) or `system_profiler SPUSBDataType` (Mac OS), links to external resources or already collected traffic data.

---

Finally, I can help with:¹

- [ ] testing changes on Linux
- [ ] testing changes on Windows
- [ ] testing changes on Mac OS
- [ ] attempting to capture USB traffic
- [ ] attempting to capture I²C/SMBus traffic
- [ ] analyzing traffic data
- [ ] documenting the protocol
- [ ] implementing the driver

¹ Assuming documentation and/or assistance will be provided.
