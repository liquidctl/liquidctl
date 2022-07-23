from ctypes import *
from ctypes.wintypes import *

_ole32 = oledll.ole32

_StringFromCLSID = _ole32.StringFromCLSID
_CoTaskMemFree = windll.ole32.CoTaskMemFree


"""Flags controlling what is included in the device information set built by SetupDiGetClassDevs"""
DIGCF_DEFAULT = 0x00000001
DIGCF_PRESENT = 0x00000002
DIGCF_ALLCLASSES = 0x00000004
DIGCF_PROFILE = 0x00000008
DIGCF_DEVICE_INTERFACE = 0x00000010

"""Flags controlling File acccess"""
GENERIC_WRITE = (1073741824)
GENERIC_READ = (-2147483648)
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
FILE_ATTRIBUTE_NORMAL = 128
FILE_FLAG_OVERLAPPED = 1073741824

INVALID_HANDLE_VALUE = HANDLE(-1)

""" USB PIPE TYPE """
PIPE_TYPE_CONTROL = 0
PIPE_TYPE_ISO = 1
PIPE_TYPE_BULK = 2
PIPE_TYPE_INTERRUPT = 3


""" Errors """
ERROR_IO_INCOMPLETE = 996
ERROR_IO_PENDING = 997


class UsbSetupPacket(Structure):
    _fields_ = [("request_type", c_ubyte), ("request", c_ubyte),
                ("value", c_ushort), ("index", c_ushort), ("length", c_ushort)]


class Overlapped(Structure):
    _fields_ = [('Internal', LPVOID),
                ('InternalHigh', LPVOID),
                ('Offset', DWORD),
                ('OffsetHigh', DWORD),
                ('Pointer', LPVOID),
                ('hEvent', HANDLE),]


class UsbInterfaceDescriptor(Structure):
    _fields_ = [("b_length", c_ubyte), ("b_descriptor_type", c_ubyte),
                ("b_interface_number", c_ubyte), ("b_alternate_setting", c_ubyte),
                ("b_num_endpoints", c_ubyte), ("b_interface_class", c_ubyte),
                ("b_interface_sub_class", c_ubyte), ("b_interface_protocol", c_ubyte),
                ("i_interface", c_ubyte)]


class PipeInfo(Structure):
    _fields_ = [("pipe_type", c_ulong,), ("pipe_id", c_ubyte),
                ("maximum_packet_size", c_ushort), ("interval", c_ubyte)]


class LpSecurityAttributes(Structure):
    _fields_ = [("n_length", DWORD), ("lp_security_descriptor", c_void_p),
                ("b_Inherit_handle", BOOL)]


class GUID(Structure):
    _fields_ = [("data1", DWORD), ("data2", WORD),
                ("data3", WORD), ("data4", c_byte * 8)]

    def __repr__(self):
        return u'GUID("%s")' % str(self)

    def __str__(self):
        p = c_wchar_p()
        _StringFromCLSID(byref(self), byref(p))
        result = p.value
        _CoTaskMemFree(p)
        return result

    def __cmp__(self, other):
        if isinstance(other, GUID):
            a = bytes(self)
            b = bytes(other)
            return (a > b) - (a < b)
        return -1

    def __nonzero__(self):
        return self != GUID_null

    def __eq__(self, other):
        return isinstance(other, GUID) and \
               bytes(self) == bytes(other)

    def __hash__(self):
        # We make GUID instances hashable, although they are mutable.
        return hash(bytes(self))


GUID_null = GUID()


class SpDevinfoData(Structure):
    _fields_ = [("cb_size", DWORD), ("class_guid", GUID),
                ("dev_inst", DWORD), ("reserved", POINTER(c_ulong))]


class SpDeviceInterfaceData(Structure):
    _fields_ = [("cb_size", DWORD), ("interface_class_guid", GUID),
                ("flags", DWORD), ("reserved", POINTER(c_ulong))]


class SpDeviceInterfaceDetailData(Structure):
    _fields_ = [("cb_size", DWORD), ("device_path", WCHAR * 1)]  # devicePath array!!!
