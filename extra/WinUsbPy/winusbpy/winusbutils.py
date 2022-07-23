from ctypes import *
from ctypes.wintypes import *
from .winusbclasses import (
    UsbSetupPacket,
    Overlapped,
    UsbInterfaceDescriptor,
    LpSecurityAttributes,
    GUID,
    SpDevinfoData,
    SpDeviceInterfaceData,
    SpDeviceInterfaceDetailData,
    PipeInfo,
)

WinUsb_Initialize = "WinUsb_Initialize"
WinUsb_ControlTransfer = "WinUsb_ControlTransfer"
WinUsb_GetDescriptor = "WinUsb_GetDescriptor"
WinUsb_GetOverlappedResult = "WinUsb_GetOverlappedResult"
WinUsb_SetPipePolicy = "WinUsb_SetPipePolicy"
WinUsb_ReadPipe = "WinUsb_ReadPipe"
WinUsb_WritePipe = "WinUsb_WritePipe"
WinUsb_FlushPipe = "WinUsb_FlushPipe"
WinUsb_Free = "WinUsb_Free"
WinUsb_QueryDeviceInformation = "WinUsb_QueryDeviceInformation"
WinUsb_QueryInterfaceSettings = "WinUsb_QueryInterfaceSettings"
WinUsb_GetAssociatedInterface = "WinUsb_GetAssociatedInterface"
WinUsb_QueryPipe = "WinUsb_QueryPipe"
# WinUsb_ControlTransfer = "WinUsb_ControlTransfer"
# WinUsb_QueryPipe = "WinUsb_QueryPipe"
Close_Handle = "CloseHandle"
CreateFile = "CreateFileW"
ReadFile = "ReadFile"
CancelIo = "CancelIo"
WriteFile = "WriteFile"
SetEvent = "SetEvent"
WaitForSingleObject = "WaitForSingleObject"
GetLastError = "GetLastError"
SetupDiGetClassDevs = "SetupDiGetClassDevs"
SetupDiEnumDeviceInterfaces = "SetupDiEnumDeviceInterfaces"
SetupDiGetDeviceInterfaceDetail = "SetupDiGetDeviceInterfaceDetail"
SetupDiGetDeviceRegistryProperty = "SetupDiGetDeviceRegistryProperty"
SetupDiEnumDeviceInfo = "SetupDiEnumDeviceInfo"

SPDRP_HARDWAREID = 1
SPDRP_FRIENDLYNAME = 12
SPDRP_LOCATION_PATHS = 35
SPDRP_MFG = 11


def get_winusb_functions(windll):
    """Functions availabe from WinUsb dll and their types"""
    winusb_dict = {}
    winusb_functions = {}
    winusb_restypes = {}
    winusb_argtypes = {}

    # BOOL __stdcall WinUsb_Initialize( _In_ HANDLE DeviceHandle,_Out_  PWINUSB_INTERFACE_HANDLE InterfaceHandle);
    winusb_functions[WinUsb_Initialize] = windll.WinUsb_Initialize
    winusb_restypes[WinUsb_Initialize] = BOOL
    winusb_argtypes[WinUsb_Initialize] = [HANDLE, POINTER(c_void_p)]

    # BOOL __stdcall WinUsb_ControlTransfer(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ WINUSB_SETUP_PACKET SetupPacket, _Out_ PUCHAR Buffer,_In_ ULONG BufferLength,_Out_opt_  PULONG LengthTransferred,_In_opt_  LPOVERLAPPED Overlapped);
    winusb_functions[WinUsb_ControlTransfer] = windll.WinUsb_ControlTransfer
    # winusb_restypes[WinUsb_ControlTransfer] = BOOL
    # winusb_argtypes[WinUsb_ControlTransfer] = [c_void_p, UsbSetupPacket, POINTER(c_ubyte), c_ulong, POINTER(c_ulong), LpOverlapped]

    # BOOL __stdcall WinUsb_GetDescriptor(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ UCHAR DescriptorType,_In_ UCHAR Index,_In_ USHORT LanguageID,_Out_ PUCHAR Buffer,_In_ ULONG BufferLength,_Out_ PULONG LengthTransferred);
    winusb_functions[WinUsb_GetDescriptor] = windll.WinUsb_GetDescriptor
    winusb_restypes[WinUsb_GetDescriptor] = BOOL
    winusb_argtypes[WinUsb_GetDescriptor] = [
        c_void_p,
        c_ubyte,
        c_ubyte,
        c_ushort,
        POINTER(c_ubyte),
        c_ulong,
        POINTER(c_ulong),
    ]

    # BOOL __stdcall WinUsb_GetOverlappedResult(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ LPOVERLAPPED lpOverlapped,_Out_ LPDWORD lpNumberOfBytesTransferred,_In_ BOOL bWait);
    winusb_functions[WinUsb_GetOverlappedResult] = windll.WinUsb_GetOverlappedResult
    winusb_restypes[WinUsb_GetOverlappedResult] = BOOL
    # winusb_argtypes[WinUsb_GetOverlappedResult] = []

    # BOOL __stdcall WinUsb_ReadPipe( _In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ UCHAR PipeID,_Out_ PUCHAR Buffer,_In_ ULONG BufferLength,_Out_opt_ PULONG LengthTransferred,_In_opt_ LPOVERLAPPED Overlapped);
    winusb_functions[WinUsb_ReadPipe] = windll.WinUsb_ReadPipe
    # winusb_restypes[WinUsb_ReadPipe] = BOOL
    # winusb_argtypes[WinUsb_ReadPipe] = [c_void_p, c_ubyte, POINTER(c_ubyte), c_ulong, POINTER(c_ulong), LpOverlapped]

    # BOOL __stdcall WinUsb_ReadPipe( _In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ UCHAR PipeID,_Out_ PUCHAR Buffer,_In_ ULONG BufferLength,_Out_opt_ PULONG LengthTransferred,_In_opt_ LPOVERLAPPED Overlapped);
    winusb_functions[WinUsb_SetPipePolicy] = windll.WinUsb_SetPipePolicy
    winusb_restypes[WinUsb_SetPipePolicy] = BOOL
    winusb_argtypes[WinUsb_SetPipePolicy] = [c_void_p, c_ubyte, c_ulong, c_ulong, c_void_p]

    # BOOL __stdcall WinUsb_WritePipe(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ UCHAR PipeID,_In_ PUCHAR Buffer,_In_ ULONG BufferLength,_Out_opt_  PULONG LengthTransferred,_In_opt_ LPOVERLAPPED Overlapped);
    winusb_functions[WinUsb_WritePipe] = windll.WinUsb_WritePipe
    # winusb_restypes[WinUsb_WritePipe] = BOOL
    # winusb_argtypes[WinUsb_WritePipe] = [c_void_p, c_ubyte, POINTER(c_ubyte), c_ulong, POINTER(c_ulong), LpOverlapped]

    # BOOL __stdcall WinUsb_FlushPipe(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle);
    winusb_functions[WinUsb_FlushPipe] = windll.WinUsb_FlushPipe
    winusb_restypes[WinUsb_FlushPipe] = BOOL
    winusb_argtypes[WinUsb_FlushPipe] = [c_void_p, c_ubyte]

    # BOOL __stdcall WinUsb_Free(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle);
    winusb_functions[WinUsb_Free] = windll.WinUsb_Free
    winusb_restypes[WinUsb_Free] = BOOL
    winusb_argtypes[WinUsb_Free] = [c_void_p]

    # BOOL __stdcall WinUsb_QueryDeviceInformation(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ ULONG InformationType,_Inout_ PULONG BufferLength,_Out_ PVOID Buffer);
    winusb_functions[WinUsb_QueryDeviceInformation] = windll.WinUsb_QueryDeviceInformation
    winusb_restypes[WinUsb_QueryDeviceInformation] = BOOL
    winusb_argtypes[WinUsb_QueryDeviceInformation] = [c_void_p, c_ulong, POINTER(c_ulong), c_void_p]

    # BOOL __stdcall WinUsb_QueryInterfaceSettings(_In_ WINUSB_INTERFACE_HANDLE InterfaceHandle,_In_ UCHAR AlternateSettingNumber,_Out_ PUSB_INTERFACE_DESCRIPTOR UsbAltInterfaceDescriptor);
    winusb_functions[WinUsb_QueryInterfaceSettings] = windll.WinUsb_QueryInterfaceSettings
    winusb_restypes[WinUsb_QueryInterfaceSettings] = BOOL
    winusb_argtypes[WinUsb_QueryInterfaceSettings] = [
        c_void_p,
        c_ubyte,
        POINTER(UsbInterfaceDescriptor),
    ]

    winusb_functions[WinUsb_QueryPipe] = windll.WinUsb_QueryPipe
    winusb_restypes[WinUsb_QueryPipe] = BOOL
    winusb_argtypes[WinUsb_QueryPipe] = [c_void_p, c_ubyte, c_ubyte, POINTER(PipeInfo)]

    winusb_functions[WinUsb_GetAssociatedInterface] = windll.WinUsb_GetAssociatedInterface
    winusb_restypes[WinUsb_GetAssociatedInterface] = BOOL
    winusb_argtypes[WinUsb_GetAssociatedInterface] = [c_void_p, c_ubyte, POINTER(c_void_p)]

    winusb_dict["functions"] = winusb_functions
    winusb_dict["restypes"] = winusb_restypes
    winusb_dict["argtypes"] = winusb_argtypes
    return winusb_dict


def get_kernel32_functions(kernel32):
    kernel32_dict = {}
    kernel32_functions = {}
    kernel32_restypes = {}
    kernel32_argtypes = {}

    # BOOL WINAPI CloseHandle(_In_  HANDLE hObject);
    kernel32_functions[Close_Handle] = kernel32.CloseHandle
    kernel32_restypes[Close_Handle] = BOOL
    kernel32_argtypes[Close_Handle] = [HANDLE]

    # BOOL WINAPI ReadFile(_In_ HANDLE hFile,_Out_ LPVOID lpBuffer,_In_ DWORD nNumberOfBytesToRead,_Out_opt_ LPDWORD lpNumberOfBytesRead,_Inout_opt_ LPOVERLAPPED lpOverlapped);
    kernel32_functions[ReadFile] = kernel32.ReadFile
    kernel32_restypes[ReadFile] = BOOL
    kernel32_argtypes[ReadFile] = [HANDLE, c_void_p, DWORD, POINTER(DWORD), POINTER(Overlapped)]

    # BOOL WINAPI CancelIo(_In_  HANDLE hFile);
    kernel32_functions[CancelIo] = kernel32.CancelIo
    kernel32_restypes[CancelIo] = BOOL
    kernel32_argtypes[CancelIo] = [HANDLE]

    # BOOL WINAPI WriteFile(_In_ HANDLE hFile,_In_ LPCVOID lpBuffer,_In_ DWORD nNumberOfBytesToWrite,_Out_opt_ LPDWORD lpNumberOfBytesWritten,_Inout_opt_  LPOVERLAPPED lpOverlapped);
    kernel32_functions[WriteFile] = kernel32.WriteFile
    kernel32_restypes[WriteFile] = BOOL
    kernel32_argtypes[WriteFile] = [HANDLE, c_void_p, DWORD, POINTER(DWORD), POINTER(Overlapped)]

    # BOOL WINAPI SetEvent(_In_ HANDLE hEvent);
    kernel32_functions[SetEvent] = kernel32.SetEvent
    kernel32_restypes[SetEvent] = BOOL
    kernel32_argtypes[SetEvent] = [HANDLE]

    # DWORD WINAPI WaitForSingleObject(_In_ HANDLE hHandle, _In_  DWORD dwMilliseconds);
    kernel32_functions[WaitForSingleObject] = kernel32.WaitForSingleObject
    kernel32_restypes[WaitForSingleObject] = DWORD
    kernel32_argtypes[WaitForSingleObject] = [HANDLE, DWORD]

    # HANDLE WINAPI CreateFile(_In_ LPCTSTR lpFileName,_In_ DWORD dwDesiredAccess,_In_ DWORD dwShareMode,_In_opt_ LPSECURITY_ATTRIBUTES lpSecurityAttributes,_In_ DWORD dwCreationDisposition,_In_ DWORD dwFlagsAndAttributes,_In_opt_ HANDLE hTemplateFile);
    kernel32_functions[CreateFile] = kernel32.CreateFileW
    kernel32_restypes[CreateFile] = HANDLE

    # DWORD WINAPI GetLastError(void)
    kernel32_functions[GetLastError] = kernel32.GetLastError
    kernel32_restypes[GetLastError] = DWORD
    kernel32_argtypes[GetLastError] = []

    kernel32_dict["functions"] = kernel32_functions
    kernel32_dict["restypes"] = kernel32_restypes
    kernel32_dict["argtypes"] = kernel32_argtypes
    return kernel32_dict


def get_setupapi_functions(setupapi):
    setupapi_dict = {}
    setupapi_functions = {}
    setupapi_restypes = {}
    setupapi_argtypes = {}

    # HDEVINFO SetupDiGetClassDevs(_In_opt_ const GUID *ClassGuid,_In_opt_ PCTSTR Enumerator,_In_opt_ HWND hwndParent,_In_ DWORD Flags);
    setupapi_functions[SetupDiGetClassDevs] = setupapi.SetupDiGetClassDevsW
    setupapi_restypes[SetupDiGetClassDevs] = HANDLE
    setupapi_argtypes[SetupDiGetClassDevs] = [POINTER(GUID), c_wchar_p, HANDLE, DWORD]

    # BOOL SetupDiEnumDeviceInterfaces(_In_ HDEVINFO DeviceInfoSet,_In_opt_ PSP_DEVINFO_DATA DeviceInfoData,_In_ const GUID *InterfaceClassGuid,_In_ DWORD MemberIndex,_Out_ PSP_DEVICE_INTERFACE_DATA DeviceInterfaceData);
    setupapi_functions[SetupDiEnumDeviceInterfaces] = setupapi.SetupDiEnumDeviceInterfaces
    setupapi_restypes[SetupDiEnumDeviceInterfaces] = BOOL
    setupapi_argtypes[SetupDiEnumDeviceInterfaces] = [
        c_void_p,
        POINTER(SpDevinfoData),
        POINTER(GUID),
        DWORD,
        POINTER(SpDeviceInterfaceData),
    ]

    # BOOL SetupDiGetDeviceInterfaceDetail(_In_ HDEVINFO DeviceInfoSet,_In_ PSP_DEVICE_INTERFACE_DATA DeviceInterfaceData,_Out_opt_ PSP_DEVICE_INTERFACE_DETAIL_DATA DeviceInterfaceDetailData,_In_ DWORD DeviceInterfaceDetailDataSize,_Out_opt_  PDWORD RequiredSize,_Out_opt_  PSP_DEVINFO_DATA DeviceInfoData);
    setupapi_functions[SetupDiGetDeviceInterfaceDetail] = setupapi.SetupDiGetDeviceInterfaceDetailW
    setupapi_restypes[SetupDiGetDeviceInterfaceDetail] = BOOL
    setupapi_argtypes[SetupDiGetDeviceInterfaceDetail] = [
        c_void_p,
        POINTER(SpDeviceInterfaceData),
        POINTER(SpDeviceInterfaceDetailData),
        DWORD,
        POINTER(DWORD),
        POINTER(SpDevinfoData),
    ]

    # BOOL SetupDiGetDeviceInterfaceDetail(_In_ HDEVINFO DeviceInfoSet,_In_ PSP_DEVICE_INTERFACE_DATA DeviceInterfaceData,_Out_opt_ PSP_DEVICE_INTERFACE_DETAIL_DATA DeviceInterfaceDetailData,_In_ DWORD DeviceInterfaceDetailDataSize,_Out_opt_  PDWORD RequiredSize,_Out_opt_  PSP_DEVINFO_DATA DeviceInfoData);
    setupapi_functions[
        SetupDiGetDeviceRegistryProperty
    ] = setupapi.SetupDiGetDeviceRegistryPropertyW
    setupapi_restypes[SetupDiGetDeviceRegistryProperty] = BOOL
    setupapi_argtypes[SetupDiGetDeviceRegistryProperty] = [
        c_void_p,
        POINTER(SpDevinfoData),
        DWORD,
        POINTER(DWORD),
        c_void_p,
        DWORD,
        POINTER(DWORD),
    ]
    # [HDEVINFO, PSP_DEVINFO_DATA, DWORD, PDWORD, PBYTE, DWORD, PDWORD]

    # BOOL SetupDiEnumDeviceInfo(HDEVINFO DeviceInfoSet, DWORD MemberIndex, PSP_DEVINFO_DATA DeviceInfoData);
    setupapi_functions[SetupDiEnumDeviceInfo] = setupapi.SetupDiEnumDeviceInfo
    setupapi_restypes[SetupDiEnumDeviceInfo] = BOOL
    setupapi_argtypes[SetupDiEnumDeviceInfo] = [c_void_p, DWORD, POINTER(SpDevinfoData)]

    setupapi_dict["functions"] = setupapi_functions
    setupapi_dict["restypes"] = setupapi_restypes
    setupapi_dict["argtypes"] = setupapi_argtypes
    return setupapi_dict


def is_device(vid, pid, path, name=None):
    # this is not working
    # not used
    # replaced by extract_device_from_vid_pid

    if name and name.lower() == path.lower():
        return True
    if vid and pid:
        if (
            path.lower().find("vid_%04x" % int(str(vid), 0)) != -1
            and path.lower().find("pid_%04x" % int(str(pid), 0)) != -1
        ):
            return True
    else:
        return False
