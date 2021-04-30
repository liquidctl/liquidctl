# Porting drivers from OpenCorsairLink

_Originally posted as a [comment in issue #129](https://github.com/liquidctl/liquidctl/issues/129#issuecomment-640258429)._

In essence, writing a new liquidctl driver means implementing all (suitable) methods of a [`liquidctl.base.BaseDriver`](https://github.com/liquidctl/liquidctl/blob/main/liquidctl/driver/base.py#L9).
 
Note that you shouldn't _directly_ subclass the BaseDriver; instead you'll inherit from a bus-specific base driver like `liquidctl.usb.UsbDriver` or `liquidctl.usb.UsbHidDevice`, which will already include default implementations for many methods and properties.

And for the new driver to work out-of-the-box it's sufficient to import its module in [`liquidctl/driver/__init__.py`](https://github.com/liquidctl/liquidctl/blob/main/liquidctl/driver/__init__.py#L23).

Next, in order to port a driver from OCL, the first step is to check the `corsair_device_info` struct that matches the device, which defines the low-level and driver (protocol) functions used for it in OCL, besides a few other important parameters.

```c
    {
        .vendor_id = 0x1b1c,
        .product_id = 0x0c04,
        .device_id = 0x3b,
        .name = "H80i",
        .read_endpoint = 0x01 | LIBUSB_ENDPOINT_IN,
        .write_endpoint = 0x00 | LIBUSB_ENDPOINT_OUT,
        .driver = &corsairlink_driver_coolit,
        .lowlevel = &corsairlink_lowlevel_coolit,
        .led_control_count = 1,
        .fan_control_count = 4,
        .pump_index = 5,
    },
```
—_[in `device.c`](https://github.com/audiohacked/OpenCorsairLink/blob/61d336a61b85705a5e128762430dc136460b110e/device.c#L107-L119)_

## The low-level functions

Starting with the low-level functions specified by [`corsairlink_lowlevel_coolit`](https://github.com/audiohacked/OpenCorsairLink/blob/61d336a61b85705a5e128762430dc136460b110e/drivers/coolit.c#L27-L32), and implemented in [`lowlevel/coolit.c`](https://github.com/audiohacked/OpenCorsairLink/blob/61d336a61b85705a5e128762430dc136460b110e/lowlevel/coolit.c): the equivalence between these and the methods in a liquidctl driver is:

-  `init` -> `connect` (in some cases and/or `initialize`)
- `deinit` -> `disconnect`
- `read`/`write` -> `self.device.read`/`self.device.write` (see next paragraphs)

This is a HID device, so the liquidctl driver should inherit [`liquidctl.usb.UsbHidDriver`](https://github.com/liquidctl/liquidctl/blob/c9f2244200a552ce8af3d64b937d3b01cebdb126/liquidctl/driver/usb.py), meaning that in the driver `self.device` will be a `liquidctl.usb.HidapiDevice`.  Additionally, liquidctl already automatically handles how to write to a HID, but does so mimicking hidapi; `HidapiDevice.write` follows the specification:

> The first byte of data[] must contain the Report ID. For devices which only support a single report, this must be set to 0x0. The remaining bytes contain the report data. Since the Report ID is mandatory, calls to hid_write() will always contain one more byte than the report contains.
>—_from [`hidapi/hidapi.h`](https://github.com/libusb/hidapi/blob/24a822c80f95ae1b46a7a3c16008858dc4d8aec8/hidapi/hidapi.h#L185-L213)_

Practically, it means that you only need to implement `init` and `deinit`, and that in the translated driver, when OCL would call `corsairlink_coolit_write` with `[byte1, byte2, byte3, ...]`, you'll instead call `self.device.write` with `[0x00, byte1, byte2, byte3, ...]` (note the prepended 0x00 byte)

## Higher-level functionality

The remaining `get_status`, `set_fixed_speed`, `set_speed_profile` and `set_color` methods (required by BaseDriver) will encapsulate the functionality specified by [`corsairlink_driver_coolit`](https://github.com/audiohacked/OpenCorsairLink/blob/61d336a61b85705a5e128762430dc136460b110e/drivers/coolit.c#L34) (implemented in `protocol/coolit/*.c`), and are for the most part what users will access through the CLI.

Data that is read from the cooler, like the pump speed, will generally go into `get_status`.  The firmware version is an exception in this case: it's read with a specific command (instead of being part of other replies), and so it belongs in the output of `initialize`.

_(You can fetch the firmware version directly in `initialize` or, if you need to use it anywhere else, you read it and cache it in `connect`, and only return the cached value in `initialize`.)_

The other three methods are self-explanatory and should be fairly straightforward to implement, apart from the special considerations that I go into next.

## Protocols with _interdependent_ messages

A big aspect in the design of the liquidctl CLI was not requiring the user to configure different aspects of the cooler in a single command: you should be able to set the pump speed without resetting the fan speed or the LED colors.

For most devices there's a clear mapping between the CLI and the implementation: the CLI command `set <channel> speed <fixed duty>` implemented with `set_fixed_speed` won't depend on other BaseDriver methods (apart from `connect` and `disconnect`).

There are however "complicated" devices where, at the protocol level, functionality is grouped (all channels must be set at once) or even completely consolidated into a single "state" (everything must be reset when changing a single parameter).  Messages can also be required to follow an arbitrary order.

So, besides looking at how each individual parameter is configured, you also need to check the "logic" part of OCL, in this case implemented in [`hydro_coolit_settings`](https://github.com/audiohacked/OpenCorsairLink/blob/testing/logic/settings/hydro_coolit.c#L32).  This doesn't mean that all OCL devices will fall into the "complicated" category, or that you'll necessarily need to match that order exactly.

In fact, in the case of the H80i (or other devices using the same protocol) I think that the different aspects of the cooler can indeed be configured independently, at least for the most part.

This is mostly due to the empty implementations of `init` and `deinit`: in more complex cases these functions usually involve some type of opening and closing of a "transaction", but there's nothing of the sort here.

The ordering in `hydro_coolit_settings` also seems to be strictly due to natural requirements (you need to know how many sensors there are before reading them), instead of being totally arbitrary.  But I could be wrong...

Anyway, the main concern I have right now is the [`CommandId`](https://github.com/audiohacked/OpenCorsairLink/blob/61d336a61b85705a5e128762430dc136460b110e/include/protocol/coolit.h#L93) byte that's sent in every message. 
 It starts at 0x81 and is continually incremented.  On one hand it clearly doesn't need to be a perfect sequence number (as OCL doesn't guarantee that in multiple invocations), but on the other the shorter message chains in liquidctl (due to only a few parameters being read or changed at a time) could cause the cooler to complain.

I'd start following OCL: initialize a similar variable to 0x81 every time the driver is instantiated, and increment it every time it's used.  But if that somehow doesn't work, you can use the internal [`keyval`](https://github.com/liquidctl/liquidctl/blob/main/liquidctl/keyval.py#L1) API ([example usage](https://github.com/liquidctl/liquidctl/blob/4e649bead665bf692d7df9b8bc1a9a79791d356d/liquidctl/driver/asetek.py#L281)) to temporarily persist it to disk, allowing you to implement a true (wrapping) sequence number _across_ liquidctl invocations.

No matter what, just don't forget to explicitly wrap `CommandId` it at 255, you'll probably be using a normal Python integer instead of a `u8`.

## Advanced driver binding

liquidctl driver don't normally need to check anything super special to know whether or not they are compatible with a particular device.  As long as `SUPPORTED_DEVICES` lists the compatible USB vendor and product IDs, besides any additional parameters required by `__init__`, the bus-specific base driver will do the rest.

This wont be the case with the H80i: it shares a common vendor and product ID with other devices, and is only differentiated by a "device ID", that has to be explicitly read.  Reading of this device ID is implemented in OCL by [`corsairlink_coolit_device_id`](https://github.com/audiohacked/OpenCorsairLink/blob/61d336a61b85705a5e128762430dc136460b110e/protocol/coolit/core.c#L32).

There are two ways of handling this in liquidctl.  One way is to override `probe` (implemented in `UsbHidDriver`) to fetch the device ID, filter out any unknown IDs, and (only) yield driver instances that have as field a know ID; each instance should also map that ID to the corresponding parameters for that device (`description`, fan count, pump index, etc.).  Another way is to have a generic driver that only fetches the ID and customizes itself accordingly at `connect` time, meaning that before that it identifies itself as something like "Undetermined Corsair device".

Because having the driver instance in an undetermined state will cause some issues, both for us and for the user, I think you should try the `probe` method first.
