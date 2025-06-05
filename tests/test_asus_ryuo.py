import pytest

from _testutils import MockHidapiDevice
from liquidctl.driver.asus_ryuo import AsusRyuo

@pytest.fixture
def mockRyuo():
    return AsusRyuo(_MockRyuoDevice(), "Mock Asus Ryuo I"

class _MockRyuoDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__()
