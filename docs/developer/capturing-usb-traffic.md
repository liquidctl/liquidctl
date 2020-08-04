# Capturing USB traffic

## Preface

A fundamental aspect of developing drivers for USB devices is inspecting the
traffic between applications and the device.

This is useful for debugging your own drivers and applications, as well as to
understand undocumented protocols.

In the latter case, a possibly opaque and closed source application is allowed
to communicate with the device, and the captured traffic is analyzed to
understand what the device is capable of and what it expects from the host
application.

## Capturing USB traffic on a native Windows host

Get [Wireshark].  During the Wireshark setup, enable the installation of
USBPcap for experimental capturing of USB traffic.  Reboot.

To capture some USB traffic, start Wireshark, double click the USBPcap1
interface to start capturing all traffic on it, and proceed to [Finding the
target device].

_If you have more than one USBPcap interface, you may need to look for the
target devices in each of them._

## Capturing USB traffic on Linux
_and capturing USB traffic in a Windows VM, through the Linux host_

To be written.

## Finding the target device
[Finding the target device](#finding-the-target-device)

Wireshark captures USB traffic at the bus level, which means that all devices
on that bus will be captured.  This is a lot of noise, so the first step is
find the target device among all others and filter the traffic to that device.

_For this example, assume the target device has vendor and product IDs `0x1e71`
and `0x170e`, respectively._

First, filter (top bar) the `GET DESCRIPTOR` response for this device:

```
usb.idVendor == 0x1e71 && usb.idProduct == 0x170e
```

Next, select the filtered packet and, on the middle panel, expand the USB URB
details, right click "Device address" and select Apply as Filter -> Selected.

This should result in a new filter that resembles:

```
usb.device_address == 2
```

And only packets to or from that device should be displayed.

## Exporting captured data

There are two main useful ways to work with Wireshark captures of USB traffic.

The first is within Wireshark itself, using its native PCAP format (or any of
its variants), which is useful for manual analysis.  _PCAP files are also the
preferred way of storing and sharing captured USB traffic._

You can simply File -> Save to export captured traffic from Wireshark.  But for
more control over what will be exported (for example, only currently
filtered/displayed packets), File -> Export Specified Packets is generally
preferred.

The other way of analyzing USB traffic is through external, and sometimes
custom, tools.  In theses cases it may be helpful to additionally export the
data to JSON (File -> Export Packet Dissections -> As JSON).  Plain text or CSV
dissections are _not_ very useful with USB data, since Wireshark tends to
truncate the long fields that are of our interest.

## Next steps

To be written.

[Wireshark]: https://www.wireshark.org
[USBPcap]: https://desowin.org/usbpcap/
