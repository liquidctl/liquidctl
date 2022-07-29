import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.aquacomputer import Aquacomputer
from liquidctl.error import NotSupportedByDriver

D5NEXT_SAMPLE_STATUS_REPORT = bytes.fromhex(
    "00030DCB597C00010000006403FF00000051000004DC14000001E0007A98AF0"
    "0000000FFFF000041A803C169000001481ACAA3465CB804B401F4000000527FFF"
    "7FFF7FFF7FFF7FFF7FFF7FFF7FFF000000000000000009D27FFF00007FFF01F40"
    "4B400200026016D006300000004B200D7010207B80000000000098D083A098A08"
    "3A00060001000000000000000000000000011A24015E27101D4CFFBF"
)


@pytest.fixture
def mockD5NextDevice():
    device = _MockD5NextDevice(fw_version=1023)
    dev = Aquacomputer(
        device,
        "Mock Aquacomputer D5 Next",
        device_info=Aquacomputer.DEVICE_INFO[Aquacomputer.DEVICE_D5NEXT],
    )

    dev.connect()
    return dev


class _MockD5NextDevice(MockHidapiDevice):
    def __init__(self, fw_version):
        super().__init__(vendor_id=0x0C70, product_id=0xF00E)
        self.fw_version = fw_version

        self.preload_read(Report(1, D5NEXT_SAMPLE_STATUS_REPORT))

    def read(self, length):
        pre = super().read(length)
        if pre:
            return pre

        return Report(1, D5NEXT_SAMPLE_STATUS_REPORT)


def test_d5next_connect(mockD5NextDevice):
    def mock_open():
        nonlocal opened
        opened = True

    mockD5NextDevice.device.open = mock_open
    opened = False

    with mockD5NextDevice.connect() as cm:
        assert cm == mockD5NextDevice
        assert opened


def test_d5next_initialize(mockD5NextDevice):
    init_result = mockD5NextDevice.initialize()

    # Verify firmware version
    assert init_result[0][1] == 1023


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_d5next_get_status_directly(mockD5NextDevice, has_hwmon, direct_access):
    if has_hwmon:
        mockD5NextDevice._hwmon = HwmonDevice(None, None)

    mockD5NextDevice.device.preload_read(Report(1, D5NEXT_SAMPLE_STATUS_REPORT))

    got = mockD5NextDevice.get_status(direct_access=direct_access)

    expected = [
        ("Liquid temperature", pytest.approx(25.1, 0.1), "°C"),
        ("Pump speed", 1976, "rpm"),
        ("Pump power", pytest.approx(2.58, 0.1), "W"),
        ("Pump voltage", pytest.approx(12.02, 0.1), "V"),
        ("Pump current", pytest.approx(0.21, 0.1), "A"),
        ("Fan speed", 365, "rpm"),
        ("Fan power", pytest.approx(0.38, 0.1), "W"),
        ("Fan voltage", pytest.approx(12.04, 0.1), "V"),
        ("Fan current", pytest.approx(0.03, 0.1), "A"),
        ("+5V voltage", pytest.approx(5.00, 0.1), "V"),
        ("+12V voltage", pytest.approx(12.04, 0.1), "V"),
    ]

    assert sorted(got) == sorted(expected)


def test_d5next_get_status_from_hwmon(mockD5NextDevice, tmp_path):
    # TODO

    mockD5NextDevice._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "temp1_input").write_text("20900\n")
    (tmp_path / "fan1_input").write_text("2499\n")
    (tmp_path / "fan2_input").write_text("1702\n")

    got = mockD5NextDevice.get_status()

    expected = [
        ("Liquid temperature", pytest.approx(20.9), "°C"),
        ("Fan speed", 2499, "rpm"),
        ("Pump speed", 1702, "rpm"),
    ]

    assert sorted(got) == sorted(expected)


def test_d5next_set_fixed_speeds_not_supported(mockD5NextDevice):
    with pytest.raises(NotSupportedByDriver):
        mockD5NextDevice.set_fixed_speed("fan", 42)

        with pytest.raises(NotSupportedByDriver):
            mockD5NextDevice.set_fixed_speed("pump", 84)


def test_kraken_speed_profiles_not_supported(mockD5NextDevice):
    with pytest.raises(NotSupportedByDriver):
        mockD5NextDevice.set_speed_profile("fan", 1)

    with pytest.raises(NotSupportedByDriver):
        mockD5NextDevice.set_speed_profile("pump", 1)
