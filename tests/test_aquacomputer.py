import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.aquacomputer import Aquacomputer
from liquidctl.error import NotSupportedByDriver, NotSupportedByDevice

D5NEXT_SAMPLE_STATUS_REPORT = bytes.fromhex(
    "00030DCB597C00010000006403FF00000051000004DC14000001E0007A98AF000"
    "00000FFFF000041A803C169000001481ACAA3465CB804B401F4000000527FFF7F"
    "FF7FFF7FFF7FFF7FFF7FFF7FFF000000000000000009D27FFF00007FFF01F404B"
    "400200026016D006300000004B200D7010207B80000000000098D083A098A083A"
    "00060001000000000000000000000000011A24015E27101D4CFFBF"
)

FARBWERK360_SAMPLE_STATUS_REPORT = bytes.fromhex(
    "000141BBDE9203E80000006403FE000000110000001A150000005F0008AE3E000"
    "00023BFC8C01AA20EFFD6A0E8A3915AEC0A3C0A470A6F09F87FFF7FFF7FFF7FFF"
    "7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF00000000000000000"
    "00000000000000001F901FA0006000000030000004300000000000A0324000000"
    "00000000002710271027102710271003E8000003E8000003E8000003E80000000"
    "0000000000000000000010002000101040006"
)

OCTO_SAMPLE_STATUS_REPORT = bytes.fromhex(
    "00023A92C9EA03E80001006503FB000000010000010DB4000000C5003C3EA4010"
    "00200000000000000000000000000059EDCFFDCFFDDFFDDA7A65BF80AC60ACF0B"
    "150D600EC87FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FF"
    "F7FFF0300000000000000000000000000000004B9000300030000055D04B90001"
    "00010000000008138804B9015E006702400000000000000000000000000000000"
    "00000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000213B04B900020002000000000"
    "80000000003E8055D0000000003E800000000000003E800000000000003E80000"
    "0000000003E800000000000003E800000000000003E800000000000003E8213B0"
    "000000003E827100000000003E827100000000000000000120412862710271098"
    "20"
)


@pytest.fixture
def mockD5NextDevice():
    device = _MockD5NextDevice()
    dev = Aquacomputer(
        device,
        "Mock Aquacomputer D5 Next",
        device_info=Aquacomputer._DEVICE_INFO[Aquacomputer._DEVICE_D5NEXT],
    )

    dev.connect()
    return dev


class _MockD5NextDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0C70, product_id=0xF00E)

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

    # Verify serial number
    assert init_result[1][1] == "03531-22908"


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_d5next_get_status_directly(mockD5NextDevice, has_hwmon, direct_access):
    if has_hwmon:
        mockD5NextDevice._hwmon = HwmonDevice(None, None)

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
    mockD5NextDevice._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "temp1_input").write_text("25100\n")  # Liquid temperature
    (tmp_path / "fan1_input").write_text("1976\n")  # Pump speed
    (tmp_path / "power1_input").write_text("2580000\n")  # Pump power
    (tmp_path / "in0_input").write_text("12020\n")  # Pump voltage
    (tmp_path / "curr1_input").write_text("215\n")  # Pump current
    (tmp_path / "fan2_input").write_text("365\n")  # Fan speed
    (tmp_path / "power2_input").write_text("380000\n")  # Fan power
    (tmp_path / "in1_input").write_text("12040\n")  # Fan voltage
    (tmp_path / "curr2_input").write_text("31\n")  # Fan current
    (tmp_path / "in2_input").write_text("4990\n")  # +5V voltage
    (tmp_path / "in3_input").write_text("12040\n")  # +12V voltage

    got = mockD5NextDevice.get_status()

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


def test_d5next_set_fixed_speeds_not_supported(mockD5NextDevice):
    with pytest.raises(NotSupportedByDriver):
        mockD5NextDevice.set_fixed_speed("fan", 42)

    with pytest.raises(NotSupportedByDriver):
        mockD5NextDevice.set_fixed_speed("pump", 84)


def test_d5next_speed_profiles_not_supported(mockD5NextDevice):
    with pytest.raises(NotSupportedByDriver):
        mockD5NextDevice.set_speed_profile("fan", None)

    with pytest.raises(NotSupportedByDriver):
        mockD5NextDevice.set_speed_profile("pump", None)


@pytest.fixture
def mockFarbwerk360Device():
    device = _MockFarbwerk360Device()
    dev = Aquacomputer(
        device,
        "Mock Aquacomputer Farbwerk 360",
        device_info=Aquacomputer._DEVICE_INFO[Aquacomputer._DEVICE_FARBWERK360],
    )

    dev.connect()
    return dev


class _MockFarbwerk360Device(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0C70, product_id=0xF010)

        self.preload_read(Report(1, FARBWERK360_SAMPLE_STATUS_REPORT))

    def read(self, length):
        pre = super().read(length)
        if pre:
            return pre

        return Report(1, FARBWERK360_SAMPLE_STATUS_REPORT)


def test_farbwerk360_connect(mockFarbwerk360Device):
    def mock_open():
        nonlocal opened
        opened = True

    mockFarbwerk360Device.device.open = mock_open
    opened = False

    with mockFarbwerk360Device.connect() as cm:
        assert cm == mockFarbwerk360Device
        assert opened


def test_farbwerk360_initialize(mockFarbwerk360Device):
    init_result = mockFarbwerk360Device.initialize()

    # Verify firmware version
    assert init_result[0][1] == 1022

    # Verify serial number
    assert init_result[1][1] == "16827-56978"


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_farbwerk360_get_status_directly(mockFarbwerk360Device, has_hwmon, direct_access):
    if has_hwmon:
        mockFarbwerk360Device._hwmon = HwmonDevice(None, None)

    got = mockFarbwerk360Device.get_status(direct_access=direct_access)

    expected = [
        ("Sensor 1", pytest.approx(26.2, 0.1), "°C"),
        ("Sensor 2", pytest.approx(26.3, 0.1), "°C"),
        ("Sensor 3", pytest.approx(26.7, 0.1), "°C"),
        ("Sensor 4", pytest.approx(25.5, 0.1), "°C"),
    ]

    assert sorted(got) == sorted(expected)


def test_farbwerk360_get_status_from_hwmon(mockFarbwerk360Device, tmp_path):
    mockFarbwerk360Device._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "temp1_input").write_text("26200\n")
    (tmp_path / "temp2_input").write_text("26310\n")
    (tmp_path / "temp3_input").write_text("26710\n")
    (tmp_path / "temp4_input").write_text("25520\n")

    got = mockFarbwerk360Device.get_status()

    expected = [
        ("Sensor 1", pytest.approx(26.2, 0.1), "°C"),
        ("Sensor 2", pytest.approx(26.3, 0.1), "°C"),
        ("Sensor 3", pytest.approx(26.7, 0.1), "°C"),
        ("Sensor 4", pytest.approx(25.5, 0.1), "°C"),
    ]

    assert sorted(got) == sorted(expected)


def test_farbwerk360_set_fixed_speeds_not_supported(mockFarbwerk360Device):
    with pytest.raises(NotSupportedByDevice):
        mockFarbwerk360Device.set_fixed_speed("fan", 42)


def test_farbwerk360_speed_profiles_not_supported(mockFarbwerk360Device):
    with pytest.raises(NotSupportedByDevice):
        mockFarbwerk360Device.set_speed_profile("fan", None)


@pytest.fixture
def mockOctoDevice():
    device = _MockOctoDevice()
    dev = Aquacomputer(
        device,
        "Mock Aquacomputer Octo",
        device_info=Aquacomputer._DEVICE_INFO[Aquacomputer._DEVICE_OCTO],
    )

    dev.connect()
    return dev


class _MockOctoDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0C70, product_id=0xF011)

        self.preload_read(Report(1, OCTO_SAMPLE_STATUS_REPORT))

    def read(self, length):
        pre = super().read(length)
        if pre:
            return pre

        return Report(1, OCTO_SAMPLE_STATUS_REPORT)


def test_octo_connect(mockOctoDevice):
    def mock_open():
        nonlocal opened
        opened = True

    mockOctoDevice.device.open = mock_open
    opened = False

    with mockOctoDevice.connect() as cm:
        assert cm == mockOctoDevice
        assert opened


def test_octo_initialize(mockOctoDevice):
    init_result = mockOctoDevice.initialize()

    # Verify firmware version
    assert init_result[0][1] == 1019

    # Verify serial number
    assert init_result[1][1] == "14994-51690"


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_octo_get_status_directly(mockOctoDevice, has_hwmon, direct_access):
    if has_hwmon:
        mockOctoDevice._hwmon = HwmonDevice(None, None)

    got = mockOctoDevice.get_status(direct_access=direct_access)

    print(f"octo: got: {got}")

    expected = [
        ("Sensor 1", pytest.approx(27.5, 0.1), "°C"),
        ("Sensor 2", pytest.approx(27.7, 0.1), "°C"),
        ("Sensor 3", pytest.approx(28.4, 0.1), "°C"),
        ("Sensor 4", pytest.approx(34.2, 0.1), "°C"),
        ("Fan 1 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 1 power", pytest.approx(0.01, 0.1), "W"),
        ("Fan 1 voltage", pytest.approx(12.09, 0.1), "V"),
        ("Fan 1 current", pytest.approx(0.001, 0.1), "A"),
        ("Fan 2 speed", pytest.approx(576, 0.1), "rpm"),
        ("Fan 2 power", pytest.approx(1.03, 0.1), "W"),
        ("Fan 2 voltage", pytest.approx(12.09, 0.1), "V"),
        ("Fan 2 current", pytest.approx(0.35, 0.1), "A"),
        ("Fan 3 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 3 power", pytest.approx(0, 0.1), "W"),
        ("Fan 3 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 3 current", pytest.approx(0, 0.1), "A"),
        ("Fan 4 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 4 power", pytest.approx(0, 0.1), "W"),
        ("Fan 4 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 4 current", pytest.approx(0, 0.1), "A"),
        ("Fan 5 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 5 power", pytest.approx(0, 0.1), "W"),
        ("Fan 5 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 5 current", pytest.approx(0, 0.1), "A"),
        ("Fan 6 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 6 power", pytest.approx(0, 0.1), "W"),
        ("Fan 6 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 6 current", pytest.approx(0, 0.1), "A"),
        ("Fan 7 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 7 power", pytest.approx(0, 0.1), "W"),
        ("Fan 7 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 7 current", pytest.approx(0, 0.1), "A"),
        ("Fan 8 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 8 power", pytest.approx(0.02, 0.1), "W"),
        ("Fan 8 voltage", pytest.approx(12.09, 0.1), "V"),
        ("Fan 8 current", pytest.approx(0.002, 0.1), "A"),
    ]

    assert sorted(got) == sorted(expected)


def test_octo_get_status_from_hwmon(mockOctoDevice, tmp_path):
    mockOctoDevice._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "temp1_input").write_text("27580\n")
    (tmp_path / "temp2_input").write_text("27670\n")
    (tmp_path / "temp3_input").write_text("28370\n")
    (tmp_path / "temp4_input").write_text("34240\n")
    (tmp_path / "fan1_input").write_text("0\n")
    (tmp_path / "power1_input").write_text("10000\n")
    (tmp_path / "in0_input").write_text("12090\n")
    (tmp_path / "curr1_input").write_text("1\n")
    (tmp_path / "fan2_input").write_text("576\n")
    (tmp_path / "power2_input").write_text("1030000\n")
    (tmp_path / "in1_input").write_text("12090\n")
    (tmp_path / "curr2_input").write_text("350\n")
    (tmp_path / "fan3_input").write_text("0\n")
    (tmp_path / "power3_input").write_text("0\n")
    (tmp_path / "in2_input").write_text("0\n")
    (tmp_path / "curr3_input").write_text("0\n")
    (tmp_path / "fan4_input").write_text("0\n")
    (tmp_path / "power4_input").write_text("0\n")
    (tmp_path / "in3_input").write_text("0\n")
    (tmp_path / "curr4_input").write_text("0\n")
    (tmp_path / "fan5_input").write_text("0\n")
    (tmp_path / "power5_input").write_text("0\n")
    (tmp_path / "in4_input").write_text("0\n")
    (tmp_path / "curr5_input").write_text("0\n")
    (tmp_path / "fan6_input").write_text("0\n")
    (tmp_path / "power6_input").write_text("0\n")
    (tmp_path / "in5_input").write_text("0\n")
    (tmp_path / "curr6_input").write_text("0\n")
    (tmp_path / "fan7_input").write_text("0\n")
    (tmp_path / "power7_input").write_text("0\n")
    (tmp_path / "in6_input").write_text("0\n")
    (tmp_path / "curr7_input").write_text("0\n")
    (tmp_path / "fan8_input").write_text("0\n")
    (tmp_path / "power8_input").write_text("20000\n")
    (tmp_path / "in7_input").write_text("12090\n")
    (tmp_path / "curr8_input").write_text("2\n")

    got = mockOctoDevice.get_status()

    expected = [
        ("Sensor 1", pytest.approx(27.5, 0.1), "°C"),
        ("Sensor 2", pytest.approx(27.7, 0.1), "°C"),
        ("Sensor 3", pytest.approx(28.4, 0.1), "°C"),
        ("Sensor 4", pytest.approx(34.2, 0.1), "°C"),
        ("Fan 1 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 1 power", pytest.approx(0.01, 0.1), "W"),
        ("Fan 1 voltage", pytest.approx(12.09, 0.1), "V"),
        ("Fan 1 current", pytest.approx(0.001, 0.1), "A"),
        ("Fan 2 speed", pytest.approx(576, 0.1), "rpm"),
        ("Fan 2 power", pytest.approx(1.03, 0.1), "W"),
        ("Fan 2 voltage", pytest.approx(12.09, 0.1), "V"),
        ("Fan 2 current", pytest.approx(0.35, 0.1), "A"),
        ("Fan 3 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 3 power", pytest.approx(0, 0.1), "W"),
        ("Fan 3 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 3 current", pytest.approx(0, 0.1), "A"),
        ("Fan 4 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 4 power", pytest.approx(0, 0.1), "W"),
        ("Fan 4 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 4 current", pytest.approx(0, 0.1), "A"),
        ("Fan 5 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 5 power", pytest.approx(0, 0.1), "W"),
        ("Fan 5 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 5 current", pytest.approx(0, 0.1), "A"),
        ("Fan 6 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 6 power", pytest.approx(0, 0.1), "W"),
        ("Fan 6 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 6 current", pytest.approx(0, 0.1), "A"),
        ("Fan 7 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 7 power", pytest.approx(0, 0.1), "W"),
        ("Fan 7 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 7 current", pytest.approx(0, 0.1), "A"),
        ("Fan 8 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 8 power", pytest.approx(0.02, 0.1), "W"),
        ("Fan 8 voltage", pytest.approx(12.09, 0.1), "V"),
        ("Fan 8 current", pytest.approx(0.002, 0.1), "A"),
    ]

    assert sorted(got) == sorted(expected)


def test_octo_set_fixed_speeds_not_supported(mockOctoDevice):
    with pytest.raises(NotSupportedByDriver):
        mockOctoDevice.set_fixed_speed("fan", 42)


def test_octo_speed_profiles_not_supported(mockOctoDevice):
    with pytest.raises(NotSupportedByDriver):
        mockOctoDevice.set_speed_profile("fan", None)
