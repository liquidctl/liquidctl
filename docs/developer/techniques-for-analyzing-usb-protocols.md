# Techniques for analyzing USB protocols

_Originally posted as a [comment in issue #142](https://github.com/liquidctl/liquidctl/issues/142#issuecomment-650568291)._

## USB transfers

At a basic level you can view USB traffic as a collection of transfers.  Transfers can be of a few different types, but for the most part we're only interested in control transfers, interrupt transfers and, very occasionally, bulk transfers.  I'll skip over the purposes of each type since we'll merely use whichever ones the protocol mandates.

But our devices at not necessarily always manipulated as USB devices.  In fact, it's rather common that we need to work on a layer further up the abstraction chain, on a Human Interface Device (HID).  USB HIDs are a special type of USB device specified by a corresponding "interface class".¹

Working with HID protocols is almost identical to working with other classes of USB devices: they use control transfers and interrupt transfers, and we capture them with Wireshark.  The distinction does matter in a few places, most notability around the "report ID", but I'll get to that later...

## Wireshark, part one

So, you have captured some USB traffic to your device with Wireshark.  How do you approach that data?

First, I would filter the packets to only those coming from or being sent to the device you're interested at.  If you know the device address in the bus you can filter with `usb.device_address == <address>`, and in Linux it's easy to find the device address with `lsusb`.  I usually save these results into a new file, and only use it from that point forward.

Another way to find the device address, which can be useful when dealing with old captures or captures made in another OS or machine, it to look in the various `GET DESCRIPTOR DEVICE` responses for the one that matches the `idVendor` you're interested in.  You should know that the address on the bus can change, from OS to OS, from boot to boot or if the device is reconnected.

Next, I would add a few custom columns: `usb.data_fragment` for data sent in control transfers, and `usb.capdata` for data exchanged in the other types of transfers.

_Update: the latest versions of Wireshark have improved HID decoding capabilities, and HID data may also appear in `usbhid.data`._

Wireshark actually works one level of abstraction bellow what I called a transfer, with USB request blocks (URBs), so there's a lot of uninteresting entries in the captured data.  You can reduce this by ignoring URBs without any data_fragment or capdata, since only in a few cases these are useful in understanding the protocol.

Most of the protocol we need to implement lies in these two Wireshark fields.  In interrupt or bulk transfers all data is this `capdata`, the rest is just USB metadata.  Control transfers do need to be inspected more carefully, but their use outside of HIDs is very rare (Asetek 690LC coolers being one example).

With HIDs is common to see control transfers, particularly if the device has no OUT endpoint (an endpoint is something you write to xor read from).  In this case then all writes will be sent as control transfers (instead of interrupt transfers), usually as `SET_REPORT` requests; and this is also where the report numbers I mentioned before become important.

HIDs don't just send raw or opaque packets of bytes.  They have the concept of a report, which is supposed to structure the data and make the device capabilities self describing.  A HID can support a single unnumbered report, or one or more numbered reports.  Knowing the correct report ID (or its absence) is part of understanding the protocol, and is especially important when `SET_REPORT` transfers are involved.

![wireshark-hid-set-report2](https://user-images.githubusercontent.com/1832496/85924521-3fd19c80-b869-11ea-9bd1-43f5db6fe6ce.png)

The report ID can be decoded from `wValue` argument of the transfer: the most significant byte (MSB) is the report type (0x01 for input, 0x02 for output, 0x3 for feature) and the LSB is the report ID, or zero if the device doesn't use report IDs.  Both values are import when implementing the protocol.

Some protocols also read data from HIDs with a `GET_REPORT` request, instead of directly from the incoming endpoint.  In those cases the report type and ID will also be in `wValue`.

## Groups of transfers

Decoding the protocol involves figuring out, for each action of interest, which transfers are involved, what parameters are sent in each transfer, and how they are encoded.

The devices we're working with have two very separate sets of actions:

- reading data (usually fan/pump/temperature monitoring, but sometimes also less variable device information such as firmware version or accessories)
- writing new device configuration (fan or pump speeds, lighting animations and colors, etc.)

Sometimes reading monitoring data requires a previous write or the use of an explicit `GET_REPORT` request.  Besides obvious `GET_REPORT` requests, you may spot other protocol-specific write transfers that appear to serve no purpose other than to request data.  Other times reads will simply timeout if not preceded by a write, which you'll only discover with some experimentation.

Mapping between actions and transfers is usually simple, based on what fields you can identify in the data of each transfer.  For example, the presence of color parameters is almost always very easy to spot, and clearly indicates some type of color-related configuration.

## Common fields and field encodings

### Fan and/or pump speed (read)

Usually in u16le or u16be (16-bit unsigned integer of either endianess).  In the case of power suplies, could also be encoded in LINEAR11/LINEAR16, as defined by the PMBus specification ([`liquidctl.pmbus.linear_to_float`]).

[`liquidctl.pmbus.linear_to_float`]: https://github.com/liquidctl/liquidctl/blob/d1b8d2424948c564e218e2f0cf5ffb86f21b1445/liquidctl/pmbus.py#L104

### Fan and/or pump duty values (read/write)

Usually a single byte, either as a fraction of 100 (0–100) or 255 (0–255).

### Temperature (read)

Usually some custom type of fixed point decimal, taking two bytes.  One of the bytes is almost always `floor(temperature)`; the other is used for the remainder, encoded as a fraction of 10 (0–10) or 255 (0–255).  "Endianess" varies.

### Temperature (write)

When temperatures are sent to the device, either as part of a speed profile or to trigger visual alerts, they are almost always simple single-byte integer values (context will dictate whether should use round, floor or ceil).

### LED colors (write)

Almost universally sent as 24-bit RGB.  However, endianess varies, and some devices may also use custom orderings.  In summary, any order of 16-bit red, green and blue values for each color.

### CRC checksums (read/write)

Some devices end all messages (received and sent) with a 8-bit checksum (also known as a PEC byte).  They usually follow the SMBus specification and use the `x⁸ + x² + x¹ + x⁰` polynomial ([`liquidctl.pmbus.compute_pec(bytes)`]).

[`liquidctl.pmbus.compute_pec(bytes)`]: https://github.com/liquidctl/liquidctl/blob/d1b8d2424948c564e218e2f0cf5ffb86f21b1445/liquidctl/pmbus.py#L168

### Action type (read/write)

This indicates to the cooloer how it should interpret and act on the rest of the message.  Usually a "command" byte, but may also be the report ID.

### Sequence numbers (read/write)

Sometimes received and sent on every transfer.  May also be (shifted and) OR'ed with a "command" byte or other indicator.  You can spot this in byte offsets where the value follows a pattern that repeats every n transfers.  May or may not be required for correct operation of the device.

## Techniques for identifying fields

Spotting fields in transfers is critical.  They tell you not only where to place things, but also what each message is used for.

The first technique is simply to watch the transfers and compare, in real time, with values shown/entered in the software you're using to interact with the cooler.  This works well if the protocol is simple, and if the rate of transfers is small.  In other scenarios it doesn't work that well, but may still be required to decode specific parts of the protocol.

A related technique, particurlary when you think you're already close to understanding the protocol, is to try to read and/or write some packets yourself (make sure your writes at least resemble the real packets before trying this; sending arbitrary data to the device is a bad idea).

Next you can start to analyze the data in batches, that is, looking at a set of transactions at once.  In many cases some fields will become immediately obvious this way: you can see that there's a field, and the value will tell you what it's related to.

Taking things one step further, you can compute some basic statistics for every byte offset: min, max, average, median, ....  Even if there's a lot of noise (either from too many messages, too many unknown fields, or both) this will usually make the interesting fields more visible.

If you see a byte more or less uniformely distributed in the 0–255 range, it's likely a LSB of a two-byte field; if you see bytes with some variance but that are restricted to a specific range, just try to decode them as a fraction of 10 or 255; finally, the second byte of a two-byte field is usually (but not always) just before or just after the first.

A similar idea can be applied to bitfields: you count how many times the bit in each position changes, and this will usually tell you where the LSBs are (they are the ones that change the most).  This technique could also be applied to the entire transfer, but this isn't really necessary in the protocols we're dealing with.

While doing all/any of the above, you still want to pay some attention to the parts of the message you don't understand.  They can be "random noise" (either in the true sense or not), but there may be important things in there as well.  If you spot patterns, particularly those _not_ of a simple constant, it's worth trying to make sense of what that value could represent.  It could be a required aspect of the protocol, or an additional monitoring variable not shown in the official GUI (for example: voltage and current for a fan channel).

In the end, it comes down to spotting patterns, and besides knowing more or less what you're looking for and how it's usually encoded, you get better with experience.  But it's not very hard, it may just take more than a couple of tries in the really tricky cases.

## Wireshark, part two, and other tools

_this section is incomplete; there are many tools, and I'm not particularly good with any of them_

You should know you can export the Wireshark capture to JSON.  In fact, it's the only way I know of of getting `usb.capdata` and `usb.data_fragment` off of Wireshark into a standard data manipulation format _without truncation._

This can be done from within the Wireshark UI, or with `tshark`.

    tshark -r <filename>.pcapng -T json > <filename>.json

You can preprocess this data with `jq`, and then further manipulate it in any tool you're familiar with.  Heck, sometimes I even use spreadsheets (not very elegant, I know).

You also easily write a custom script to do some analyses or test hypothesis on these JSON captures.  For an example, check the [script I used when working the Platinum coolers].

[script I used when working the Platinum coolers]: https://github.com/liquidctl/collected-device-data/blob/master/Corsair%20H115i%20RGB%20Platinum/analyze.py



Alternatively you can use:

tshark -r <filename>.pcapng  -2 -e "frame.number" -e "usb.data_fragment" -e "usb.capdata" -Tfields  > dump.txt


To pull out only the frame number, data_fragment, and capdata fields and output them in to a txt file.
The frame number field is really usefull for if you have a seperate text description file that had a
description of what commands got set to the device and arround what frame number the message corresponds to.
(you can write down the number of one of the bottom messages shown in the wireshark console while the command is being sent)



## Notes

_¹ There are Bluetooth HIDs, but these obviously aren't very relevant here._
