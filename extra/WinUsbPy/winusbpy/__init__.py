import os
if os.name == 'nt':
	from .winusbpy import *
	from .winusb import *
else:
	raise ImportError("WinUsbPy only works on Windows platform")
