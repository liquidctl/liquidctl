from .winusberror import WinUSBError
from .winusbutils import *


class WinUSBApi(object):
    """ Facade class wrapping USB library WinUSB"""

    def __init__(self):

        try:
            self._kernel32 = windll.kernel32
        except WindowsError:
            raise WinUSBError("Kernel32 dll is not present. Are you really using Windows?")

        try:
            self._winusb = windll.winusb
        except WindowsError:
            raise WinUSBError("WinUsb dll is not present")

        try:
            self._setupapi = windll.SetupApi
        except WindowsError:
            raise WinUSBError("SetupApi dll is not present")

        self._winusb_functions_dict = get_winusb_functions(self._winusb)
        self._kernel32_functions_dict = get_kernel32_functions(self._kernel32)
        self._setupapi_functions_dict = get_setupapi_functions(self._setupapi)

    def exec_function_winusb(self, function_name, *args):
        function_caller = self._configure_ctype_function(self._winusb_functions_dict, function_name)
        return function_caller(args)

    def exec_function_kernel32(self, function_name, *args):
        function_caller = self._configure_ctype_function(self._kernel32_functions_dict, function_name)
        return function_caller(args)

    def exec_function_setupapi(self, function_name, *args):
        function_caller = self._configure_ctype_function(self._setupapi_functions_dict, function_name)
        return function_caller(args)

    def _configure_ctype_function(self, dll_dict_functions, function_name):
        def _function_caller(*args):
            function = dll_dict_functions["functions"][function_name]
            try:
                function.restype = dll_dict_functions["restypes"][function_name]
                function.argtypes = dll_dict_functions["argtypes"][function_name]
            except KeyError:
                pass
            return function(*args[0])

        return _function_caller
