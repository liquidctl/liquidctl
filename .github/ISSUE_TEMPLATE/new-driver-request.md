---
name: New Driver Request
about: To request support for a new device
title: ''
labels: new device
assignees: ''

---

**Tell us about the super awesome device you got**
Name: <what is the product name of the device>
Manufacturer: <who makes it>
How does it connect: <usb or something else?>
What does it do: <fan controller, AIO, graphics card, RAM,...>


**Did you check if it is already supported?**
- [ ] in the [README.md](README.md) device list
- [ ] in the issues requesting support for the device already
- [ ] did you check if there are any open Pull Requests for the device?


**Awesome, it seems like you have a brand new device**

- Would you be willing to test potential implementations once they are complete: *Yes/No*
- Would you be able to do the protocol analyzing / implementation effort: *Yes/No*


----
Include this for any USB based device:
```
<put the output of lsusb -v  here>
```

Could you attach some Wireshark captures between the device and the actual software?
Some documentation on how to do this can be found [here](https://github.com/liquidctl/liquidctl/blob/master/docs/developer/capturing-usb-traffic.md).
