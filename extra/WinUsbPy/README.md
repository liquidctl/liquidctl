WinUsbPy
========

WinUsbPy is a python wrapper over [WinUsblibrary](http://msdn.microsoft.com/en-us/library/windows/hardware/ff540196%28v=vs.85%29.aspx)

It contains two different layers:

- A 1:1 wrapper over WinUsb which allows calling C++ functions directly from involved dlls.
- A high level api which simplifies a lot of C++/windll/ctypes messy interactions offering just a bunch of easy methods.

Install WinUsbPy
========
~~~
python setup.py install
~~~

Low Level Api
========
Low level api offers three methods for invoking functions from three different dlls.

``` python
#args: arguments of the C++ function called
def exec_function_winusb(self, function_name, *args):
def exec_function_kernel32(self, function_name, *args):
def exec_function_setupapi(self, function_name, *args):
```

if we need to call [SetupDiGetClassDevs](http://msdn.microsoft.com/en-us/library/windows/hardware/ff551069%28v=vs.85%29.aspx) which presents this prototype:

``` c++
HDEVINFO SetupDiGetClassDevs(_In_opt_ const GUID *ClassGuid,_In_opt_ PCTSTR Enumerator,_In_opt_ HWND hwndParent,_In_ DWORD Flags);
```

``` python
from winusbpy import *
from ctypes import *
from ctypes.wintypes import *
from winusbclasses import DIGCF_DEVICE_INTERFACE, DIGCF_PRESENT

api = WinUSBApi()
byte_array = c_byte * 8
guid = GUID(0xA5DCBF10L, 0x6530, 0x11D2, byte_array(0x90, 0x1F, 0x00, 0xC0, 0x4F, 0xB9, 0x51, 0xED))
flags = DWORD(DIGCF_DEVICE_INTERFACE | DIGCF_PRESENT)

hdev_info = api.exec_function_setupapi("SetupDiGetClassDevs", byref(guid), None, None, flags)
```

[Good resources of WinUsb if you develop using this low level layer](http://msdn.microsoft.com/en-us/library/windows/hardware/ff540174(v=vs.85).aspx)

High Level Api
========
Built on top of the low level wrapper is a more usable api to perform common USB operations. Here it is list of defined functions:

``` python
# Possible keyword arguments: default, present, allclasses, profile, deviceinterface (Boolean), Usually called as follows list_usb_devices(deviceinterface=True, present=True)
def list_usb_devices(self, **kwargs):

# vid and pid must be str, returns True if device was correctly initialized and False otherwise
def init_winusb_device(self, vid, pid):

# Returns True if device was correctly closed and False otherwise.
def close_winusb_device(self):

# Returns last error code. See http://msdn.microsoft.com/en-us/library/windows/desktop/ms681382%28v=vs.85%29.aspx
def get_last_error_code(self):

# Returns information for a open device (0x03:High Speed, 0x01:full-speed or lower), query=1 in order to get USB speed.
def query_device_info(self, query=1):

# Returns a UsbInterfaceDescriptor object with information about a specified interface
def query_interface_settings(self, index):

# Change current interface, Winusb opens first interface (0 index) when a device is initialized
def change_interface(self, index):

# Returns a PipeInfo object with information of a specified pipe within current interface
def query_pipe(self, pipe_index):

# Send a control requesto to open device, setup_packet is a UsbSetupPacket object.
# buff = None implies no data is going to be transferred besides setup packet
# buff = [0] create a buffer of length 1. Buffer could be IN or OUT, direction is defined in setup packet
# it returns a dict with the response and with the buffer under the keywords 'result' and 'buffer'
def control_transfer(self, setup_packet, buff=None):

#Send Bulk data to the Usb device, write_buffer must be of type "bytes"
def write(self, pipe_id, write_buffer):

#Read Bulk data from the Usb device, Returns of a buffer not greater than length_buffer length
def read(self, pipe_id, length_buffer):
```

Let's say hello to our device:

``` python
from winusbpy import *
vid = "vid_device" # for example: VID:067b PID:2303
pid = "pid_device"

api = WinUsbPy()
result = api.list_usb_devices(deviceinterface=True, present=True)
if result:
  if api.init_winusb_device(vid, pid):

    # print device interface 0 descriptors
    interface_descriptor = api.query_interface_settings(0)
    if interface_descriptor != None:
        print("bLength: " + str(interface_descriptor.b_length))
        print("bDescriptorType: " + str(interface_descriptor.b_descriptor_type))
        print("bInterfaceNumber: " + str(interface_descriptor.b_interface_number))
        print("bAlternateSetting: " + str(interface_descriptor.b_alternate_setting))
        print("bNumEndpoints " + str(interface_descriptor.b_num_endpoints))
        print("bInterfaceClass " + str(interface_descriptor.b_interface_class))
        print("bInterfaceSubClass: " + str(interface_descriptor.b_interface_sub_class))
        print("bInterfaceProtocol: " + str(interface_descriptor.b_interface_protocol))
        print("iInterface: " + str(interface_descriptor.i_interface))

    # print device endpoint descriptors
    pipe_info_list = map(api.query_pipe, range(interface_descriptor.b_num_endpoints))
    for item in pipe_info_list:
        print("PipeType: " + str(item.pipe_type))
        print("PipeId: " + str(item.pipe_id))
        print("MaximumPacketSize: " + str(item.maximum_packet_size))
        print("Interval: " + str(item.interval))

    api.write(0x02, b"hello") # send bulk packet on OUT endpoint 2

    # close
    api.close_winusb_device()
```

Real examples
========
In "Examples" folder there are two real examples configuring a PL2303 serial usb device, listing characteristics and sending data.
[Using Low Level Api](https://github.com/felHR85/WinUsbPy/blob/master/winusbpy/examples/winusbtest.py)

[Using High Level Api](https://github.com/felHR85/WinUsbPy/blob/master/winusbpy/examples/winusbtest2.py)




