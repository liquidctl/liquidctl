import pytest
from _testutils import MockHidapiDevice, Report

from liquidctl.driver.hwmon import HwmonDevice
from liquidctl.driver.aquacomputer import Aquacomputer
from liquidctl.error import NotSupportedByDriver, NotSupportedByDevice

D5NEXT_SAMPLE_STATUS_REPORT = bytes.fromhex(
    "00030DCB597C00010000006403FF00000051000004DC14000001E0007A98AF000"
    "00000FFFF000041A803C169000001481ACAA3465CB804B401F40000005213887F"
    "FF7FFF7FFF7FFF7FFF7FFF7FFF000000000000000009D27FFF00007FFF01F404B"
    "400200026016D006300000004B200D7010207B80000000000098D083A098A083A"
    "00060001000000000000000000000000011A24015E27101D4CFFBF"
)

D5NEXT_SAMPLE_CONTROL_REPORT = bytes.fromhex(
    "00031E00000000000AC0007FFF0000000002020E100BB8000000000A0001000A0"
    "006000A000C000A0000000000000101F42710271007D000000027102710138802"
    "07D200000C8001F4012C00000064001E00010AF00A8C0AFD0B4C0B9D0BE90C460"
    "C9F0CF30D3C0DA20DE50E420E8A0EE60F350F7000000000000002D604D606D609"
    "810A010DAC1202162D17AD19D81EAE222E232E0212D300000D4801F4012C00000"
    "064001E00010AF00A8C0AFA0B4C0BA40C000C4F0CA30D110D510DA60DFD0E560E"
    "9E0EEE0F2010820000008C0000000000000000000001000180035407810A810B0"
    "10C810DD70EAC03E8FF000000000F030000FFFF0F19000003E80164000003E801"
    "FF0032006400000000000000000000000000000000000000000000FFFF0000FFF"
    "F0000FFFF0000FFFF0000FFFF0000FFFF000F0F080000FFFF0F19000003E80164"
    "000003E801FF00190028001400000000000000000000000000000000000000000"
    "00F03E7FFFF00FEFFFF0000FFFF0000FFFF0000FFFF001E0F0B0000FFFF0F1900"
    "0003E80164000003E801FF001E002800010006005000000000000000000000000"
    "0000002FF02FF01FBFFFF0525FFFF00C5FFFF03F5FFFF05F3FFFF002D0F040006"
    "FFFF0F19000003E80164000003E801FF002800050000000000000000000000000"
    "0000000000000000000000F0000FFFF01FDFFFF03FFFFFF00FAFFFF01CE10FF00"
    "3C0F040006FFFF0F19000003E80164000003E801FF00280005000000000000000"
    "00000000000000000000000000000000F00FAFFFF05DCFFFF01C2FFFF0000FFFF"
    "07D010FF004B0F040006FFFF0F19000003E80164000003E801FF0028000500000"
    "000000000000000000000000000000000000000000F03E8FFFF01C2FFFF0000FF"
    "FF0064FFFF032010FF010006030000FFFF0F19000003E80164000003E801FF001"
    "E006400000000000000000000000000000000000000000000FFFF0000FFFF0000"
    "FFFF0000FFFF0000FFFF0000FFFF010006000000FFFF0F19000003E8016400000"
    "3E80164001E006400000000000000000000000000000000000000000000FFFF00"
    "00FFFF0000FFFF0000FFFF0000FFFF0000FFFFC00401C20FA00110FB"
)

FARBWERK360_SAMPLE_STATUS_REPORT = bytes.fromhex(
    "000141BBDE9203E80000006403FE000000110000001A150000005F0008AE3E000"
    "00023BFC8C01AA20EFFD6A0E8A3915AEC0A3C0A470A6F09F814507FFF7FFF7FFF"
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

OCTO_SAMPLE_CONTROL_REPORT = bytes.fromhex(
    "000228000000A90000051402BC000000000001F42710271007D00201F42710271"
    "007D00201F42710271007D00201F42710271007D00201F42710271007D00201F4"
    "2710271007D00201F42710271007D00001F42710271007D000055DFFFF0DAC057"
    "804B000000028001400010AF00A8C0AFA0B4A0BA40BF40C4E0C9D0CF80D480DA2"
    "0DF20E4C0E9C0EF50F460FA00000008C011801F4032004B0069008D40B680E4C1"
    "194152C19281D7422102710000000FFFF0DAC057804B000000028001400010AF0"
    "0A8C0AFA0B4A0BA40BF40C4E0C9D0CF80D480DA20DF20E4C0E9C0EF50F460FA00"
    "000008C011801F4032004B0069008D40B680E4C1194152C19281D742210271000"
    "0000FFFF0DAC057804B000000028001400010AF00A8C0AFA0B4A0BA40BF40C4E0"
    "C9D0CF80D480DA20DF20E4C0E9C0EF50F460FA00000008C011801F4032004B006"
    "9008D40B680E4C1194152C19281D7422102710000000FFFF0DAC057804B000000"
    "028001400010AF00A8C0AFA0B4A0BA40BF40C4E0C9D0CF80D480DA20DF20E4C0E"
    "9C0EF50F460FA00000008C011801F4032004B0069008D40B680E4C1194152C192"
    "81D7422102710000000FFFF0DAC057804B000000028001400010AF00A8C0AFA0B"
    "4A0BA40BF40C4E0C9D0CF80D480DA20DF20E4C0E9C0EF50F460FA00000008C011"
    "801F4032004B0069008D40B680E4C1194152C19281D7422102710000000FFFF0D"
    "AC057804B000000028001400010AF00A8C0AFA0B4A0BA40BF40C4E0C9D0CF80D4"
    "80DA20DF20E4C0E9C0EF50F460FA00000008C011801F4032004B0069008D40B68"
    "0E4C1194152C19281D7422102710000000FFFF0DAC057804B0000000280014000"
    "10AF00A8C0AFA0B4A0BA40BF40C4E0C9D0CF80D480DA20DF20E4C0E9C0EF50F46"
    "0FA00000008C011801F4032004B0069008D40B680E4C1194152C19281D7422102"
    "71000213BFFFF0DAC057804B000000028001400010AF00A8C0AFA0B4A0BA40BF4"
    "0C4E0C9D0CF80D480DA20DF20E4C0E9C0EF50F460FA00000008C011801F403200"
    "4B0069008D40B680E4C1194152C19281D74221027100000FF000000000F030000"
    "FFFF0F19000003E80164000003E801FF003200640000000000000000000000000"
    "0000000000000000000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF00"
    "0F0F080000FFFF0F19000003E80164000003E801FF00190028001400000000000"
    "00000000000000000000000000000000F03E7FFFF00FEFFFF0000FFFF0000FFFF"
    "0000FFFF001E0F0B0000FFFF0F19000003E80164000003E801FF001E002800010"
    "0060050000000000000000000000000000002FF02FF01FBFFFF0525FFFF00C5FF"
    "FF03F5FFFF05F3FFFF002D0F130000FFFF0F19000003E80164000003E801FF001"
    "9000A0005000500190000000000000000000000000000000000FF0200FF780000"
    "FFFF0000FFFF0000FFFF0000FFFF003C0F040006FFFF0F19000003E8016400000"
    "3E801FF0028000500000000000000000000000000000000000000000000000F00"
    "00FFFF01FDFFFF03FFFFFF00FAFFFF01CE10FF004B0F0F0000FFFF0F19000003E"
    "80164000003E801FF00280004001E001E00000000000000000000000000000000"
    "00000000007800780000FFFF0000FFFF0000FFFF0000FFFF01000F030000FFFF0"
    "F19000003E80164000003E801FF00320064000000000000000000000000000000"
    "00000000000000FFFF0000FFFF0000FFFF0000FFFF0000FFFF0000FFFF010F0F0"
    "80000FFFF0F19000003E80164000003E801FF0019002800140000000000000000"
    "000000000000000000000000000F03E7FFFF00FEFFFF0000FFFF0000FFFF0000F"
    "FFF011E0F0B0000FFFF0F19000003E80164000003E801FF001E00280001000600"
    "50000000000000000000000000000002FF02FF01FBFFFF0525FFFF00C5FFFF03F"
    "5FFFF05F3FFFF012D0F130000FFFF0F19000003E80164000003E801FF0019000A"
    "0005000500190000000000000000000000000000000000FF0200FF780000FFFF0"
    "000FFFF0000FFFF0000FFFF013C0F040006FFFF0F19000003E80164000003E801"
    "FF0028000500000000000000000000000000000000000000000000000F0000FFF"
    "F01FDFFFF03FFFFFF00FAFFFF01CE10FF014B0F0F0000FFFF0F19000003E80164"
    "000003E801FF00280004001E001E0000000000000000000000000000000000000"
    "000007800780000FFFF0000FFFF0000FFFF0000FFFF0100001388138813881388"
    "015E01AB59"
)

QUADRO_SAMPLE_STATUS_REPORT = bytes.fromhex(
    "00035B72FF4000010000006504080000000100000013C5000000910032CBB0000"
    "0000000000000FFD5FFD69B54FFD8A6FD5B977FFF7FFF06517FFF09597FFF7FFF"
    "7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF7FFF13887FFF7FFF7FFF0300000000000"
    "000000000000300000004B9000000000000000000000000000000271004B90000"
    "0000000000000805BB04B900000000016400000015E004B900000000000000000"
    "80000000003E800000000000003E827100000000003E805BB0000000003E815E0"
    "0000000003E82710000A0000000E000000002710FF000001"
)

QUADRO_SAMPLE_CONTROL_REPORT = bytes.fromhex(
    "00031C000000A9000002580514FAEC05DC0001F42710271007D00001F42710271"
    "007D00001F42710271007D00001F42710271007D0000000FFFF0DAC057804B000"
    "000028001400010AF00A8C0AFA0B4A0BA40BF40C4E0C9D0CF80D480DA20DF20E4"
    "C0E9C0EF50F460FA00000008C011801F4032004B0069008D40B680E4C1194152C"
    "19281D7422102710004CD0FFFF0DAC057804B000000028001400010AF00A8C0AF"
    "A0B4A0BA40BF40C4E0C9D0CF80D480DA20DF20E4C0E9C0EF50F460FA00000008C"
    "011801F4032004B0069008D40B680E4C1194152C19281D74221027100005BB000"
    "30DAC057804B000000028001400010AF00A8C0AFA0B4A0BA40BF40C4E0C9D0CF8"
    "0D480DA20DF20E4C0E9C0EF50F460FA00000008C011801F4032004B0069008D40"
    "B680E4C1194152C19281D74221027100015E0FFFF0DAC057804B0000000280014"
    "00010AF00A8C0AFA0B4A0BA40BF40C4E0C9D0CF80D480DA20DF20E4C0E9C0EF50"
    "F460FA00000008C011801F4032004B0069008D40B680E4C1194152C19281D7422"
    "102710FF000200000F030000FFFF0F19000003E80164000003E801FF003200640"
    "0000000000000000000000000000000000000000000FFFF0000FFFF0000FFFF00"
    "00FFFF0000FFFF0000FFFF000F0F080000FFFF0F19000003E80164000003E801F"
    "F0019002800140000000000000000000000000000000000000000000F03E7FFFF"
    "00FEFFFF0000FFFF0000FFFF0000FFFF001E0F0B0000FFFF0F19000003E801640"
    "00003E801FF001E0028000100060050000000000000000000000000000002FF02"
    "FF01FBFFFF0525FFFF00C5FFFF03F5FFFF05F3FFFF002D0F040006FFFF0F19000"
    "003E80164000003E801FF00280005000000000000000000000000000000000000"
    "00000000000F0000FFFF01FDFFFF03FFFFFF00FAFFFF01CE10FF003C0F040006F"
    "FFF0F19000003E80164000003E801FF0028000200000000000000000000000000"
    "000000000000000000000F03FFFFFF07D0FFFF0000FFFF0000FFFF0000FFFF004"
    "B0F040006FFFF0F19000003E80164000003E801FF002800020000000000000000"
    "0000000000000000000000000000000F01CEFFFF03FFFFFF0000FFFF0000FFFF0"
    "000FFFF002D0F000006FFFF0F19000003E80164000003E8016400280002000000"
    "00000000000000000000000000000000000000000F00FAFFFF01CE10FF0000FFF"
    "F0000FFFF0000FFFF002D0F000006FFFF0F19000003E80164000003E801640028"
    "000500000000000000000000000000000000000000000000000F0000FFFF01FDF"
    "FFF03FFFFFF00FAFFFF01CE10FF0100E0A8"
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
        self.preload_read(Report(3, D5NEXT_SAMPLE_CONTROL_REPORT))
        self.preload_read(Report(3, D5NEXT_SAMPLE_CONTROL_REPORT))

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
        ("Soft. Sensor 1", pytest.approx(50, 0.1), "°C"),
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
    (tmp_path / "temp2_input").write_text("50000\n")  # Soft. Sensor 1 temperature
    (tmp_path / "temp3_input").write_text("60000\n")  # Soft. Sensor 2 temperature
    (tmp_path / "temp4_input").write_text("50000\n")  # Soft. Sensor 3 temperature
    (tmp_path / "temp5_input").write_text("50000\n")  # Soft. Sensor 4 temperature
    (tmp_path / "temp6_input").write_text("50000\n")  # Soft. Sensor 5 temperature
    (tmp_path / "temp7_input").write_text("50000\n")  # Soft. Sensor 6 temperature
    (tmp_path / "temp8_input").write_text("50000\n")  # Soft. Sensor 7 temperature
    (tmp_path / "temp9_input").write_text("50000\n")  # Soft. Sensor 8 temperature

    got = mockD5NextDevice.get_status()

    expected = [
        ("Liquid temperature", pytest.approx(25.1, 0.1), "°C"),
        ("Soft. Sensor 1", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 2", pytest.approx(60, 0.1), "°C"),
        ("Soft. Sensor 3", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 4", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 5", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 6", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 7", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 8", pytest.approx(50, 0.1), "°C"),
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


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_d5next_set_fixed_speeds_directly(mockD5NextDevice, has_hwmon, direct_access, tmp_path):
    """For both test cases only direct access should be used"""

    if has_hwmon:
        mockD5NextDevice._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "pwm1").write_text("0")
        (tmp_path / "pwm1_enable").write_text("0")
        (tmp_path / "pwm2").write_text("0")
        (tmp_path / "pwm2_enable").write_text("0")

    mockD5NextDevice.set_fixed_speed("pump", 84, direct_access=direct_access)
    mockD5NextDevice.set_fixed_speed("fan", 50, direct_access=direct_access)

    pump_report, fan_report = mockD5NextDevice.device.sent

    assert pump_report.number == 3
    assert pump_report.data[0x95:0x98] == [0, 32, 208]  # 0, <8400>
    assert fan_report.number == 3
    assert fan_report.data[0x40:0x43] == [0, 19, 136]  # 0, <5000>

    # Assert that hwmon wasn't touched
    if has_hwmon:
        assert (tmp_path / "pwm1_enable").read_text() == "0"
        assert (tmp_path / "pwm1").read_text() == "0"
        assert (tmp_path / "pwm2_enable").read_text() == "0"
        assert (tmp_path / "pwm2").read_text() == "0"


@pytest.mark.parametrize("has_support", [False, True])
def test_d5next_set_fixed_speeds_hwmon(mockD5NextDevice, has_support, tmp_path):
    mockD5NextDevice._hwmon = HwmonDevice("mock_module", tmp_path)

    if has_support:
        (tmp_path / "pwm1").write_text("0\n")
        (tmp_path / "pwm1_enable").write_text("0\n")
        (tmp_path / "pwm2").write_text("0\n")
        (tmp_path / "pwm2_enable").write_text("0\n")

    mockD5NextDevice.set_fixed_speed("pump", 84)
    mockD5NextDevice.set_fixed_speed("fan", 50)

    if has_support:
        assert (tmp_path / "pwm1_enable").read_text() == "1"
        assert (tmp_path / "pwm1").read_text() == "214"
        assert (tmp_path / "pwm2_enable").read_text() == "1"
        assert (tmp_path / "pwm2").read_text() == "127"
    else:
        # Assert fallback to direct access
        pump_report, fan_report = mockD5NextDevice.device.sent

        assert pump_report.number == 3
        assert pump_report.data[0x95:0x98] == [0, 32, 208]  # 0, <8400>
        assert fan_report.number == 3
        assert fan_report.data[0x40:0x43] == [0, 19, 136]  # 0, <5000>


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
        ("Soft. Sensor 1", pytest.approx(52.00, 0.1), "°C"),
    ]

    assert sorted(got) == sorted(expected)


def test_farbwerk360_get_status_from_hwmon(mockFarbwerk360Device, tmp_path):
    mockFarbwerk360Device._hwmon = HwmonDevice("mock_module", tmp_path)
    (tmp_path / "temp1_input").write_text("26200\n")
    (tmp_path / "temp2_input").write_text("26310\n")
    (tmp_path / "temp3_input").write_text("26710\n")
    (tmp_path / "temp4_input").write_text("25520\n")
    (tmp_path / "temp5_input").write_text("50000\n")  # Soft. Sensor 1 temperature
    (tmp_path / "temp6_input").write_text("60000\n")  # Soft. Sensor 2 temperature
    (tmp_path / "temp7_input").write_text("50000\n")  # Soft. Sensor 3 temperature
    (tmp_path / "temp8_input").write_text("50000\n")  # Soft. Sensor 4 temperature
    (tmp_path / "temp9_input").write_text("50000\n")  # Soft. Sensor 5 temperature
    (tmp_path / "temp10_input").write_text("50000\n")  # Soft. Sensor 6 temperature
    (tmp_path / "temp11_input").write_text("50000\n")  # Soft. Sensor 7 temperature
    (tmp_path / "temp12_input").write_text("50000\n")  # Soft. Sensor 8 temperature
    (tmp_path / "temp13_input").write_text("50000\n")  # Soft. Sensor 9 temperature
    (tmp_path / "temp14_input").write_text("50000\n")  # Soft. Sensor 10 temperature
    (tmp_path / "temp15_input").write_text("50000\n")  # Soft. Sensor 11 temperature
    (tmp_path / "temp16_input").write_text("50000\n")  # Soft. Sensor 12 temperature
    (tmp_path / "temp17_input").write_text("50000\n")  # Soft. Sensor 13 temperature
    (tmp_path / "temp18_input").write_text("50000\n")  # Soft. Sensor 14 temperature
    (tmp_path / "temp19_input").write_text("50000\n")  # Soft. Sensor 15 temperature
    (tmp_path / "temp20_input").write_text("50000\n")  # Soft. Sensor 16 temperature

    got = mockFarbwerk360Device.get_status()

    expected = [
        ("Sensor 1", pytest.approx(26.2, 0.1), "°C"),
        ("Sensor 2", pytest.approx(26.3, 0.1), "°C"),
        ("Sensor 3", pytest.approx(26.7, 0.1), "°C"),
        ("Sensor 4", pytest.approx(25.5, 0.1), "°C"),
        ("Soft. Sensor 1", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 2", pytest.approx(60, 0.1), "°C"),
        ("Soft. Sensor 3", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 4", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 5", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 6", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 7", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 8", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 9", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 10", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 11", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 12", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 13", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 14", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 15", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 16", pytest.approx(50, 0.1), "°C"),
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
        self.preload_read(Report(3, OCTO_SAMPLE_CONTROL_REPORT))
        self.preload_read(Report(3, OCTO_SAMPLE_CONTROL_REPORT))

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

    expected = [
        ("Sensor 1", pytest.approx(27.5, 0.1), "°C"),
        ("Sensor 2", pytest.approx(27.7, 0.1), "°C"),
        ("Sensor 3", pytest.approx(28.4, 0.1), "°C"),
        ("Sensor 4", pytest.approx(34.2, 0.1), "°C"),
        ("Soft. Sensor 1", pytest.approx(37.84, 0.1), "°C"),
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
    (tmp_path / "temp5_input").write_text("50000\n")  # Soft. Sensor 1 temperature
    (tmp_path / "temp6_input").write_text("60000\n")  # Soft. Sensor 2 temperature
    (tmp_path / "temp7_input").write_text("50000\n")  # Soft. Sensor 3 temperature
    (tmp_path / "temp8_input").write_text("50000\n")  # Soft. Sensor 4 temperature
    (tmp_path / "temp9_input").write_text("50000\n")  # Soft. Sensor 5 temperature
    (tmp_path / "temp10_input").write_text("50000\n")  # Soft. Sensor 6 temperature
    (tmp_path / "temp11_input").write_text("50000\n")  # Soft. Sensor 7 temperature
    (tmp_path / "temp12_input").write_text("50000\n")  # Soft. Sensor 8 temperature
    (tmp_path / "temp13_input").write_text("50000\n")  # Soft. Sensor 9 temperature
    (tmp_path / "temp14_input").write_text("50000\n")  # Soft. Sensor 10 temperature
    (tmp_path / "temp15_input").write_text("50000\n")  # Soft. Sensor 11 temperature
    (tmp_path / "temp16_input").write_text("50000\n")  # Soft. Sensor 12 temperature
    (tmp_path / "temp17_input").write_text("50000\n")  # Soft. Sensor 13 temperature
    (tmp_path / "temp18_input").write_text("50000\n")  # Soft. Sensor 14 temperature
    (tmp_path / "temp19_input").write_text("50000\n")  # Soft. Sensor 15 temperature
    (tmp_path / "temp20_input").write_text("50000\n")  # Soft. Sensor 16 temperature

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
        ("Soft. Sensor 1", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 2", pytest.approx(60, 0.1), "°C"),
        ("Soft. Sensor 3", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 4", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 5", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 6", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 7", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 8", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 9", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 10", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 11", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 12", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 13", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 14", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 15", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 16", pytest.approx(50, 0.1), "°C"),
    ]

    assert sorted(got) == sorted(expected)


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_octo_set_fixed_speeds_directly(mockOctoDevice, has_hwmon, direct_access, tmp_path):
    """For both test cases only direct access should be used"""

    if has_hwmon:
        mockOctoDevice._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "pwm1").write_text("0")
        (tmp_path / "pwm1_enable").write_text("0")
        (tmp_path / "pwm2").write_text("0")
        (tmp_path / "pwm2_enable").write_text("0")

    mockOctoDevice.set_fixed_speed("fan1", 84, direct_access=direct_access)
    mockOctoDevice.set_fixed_speed("fan2", 50, direct_access=direct_access)

    pump_report, fan_report = mockOctoDevice.device.sent

    assert pump_report.number == 3
    assert pump_report.data[0x59:0x5C] == [0, 32, 208]  # 0, <8400>
    assert fan_report.number == 3
    assert fan_report.data[0xAE:0xB1] == [0, 19, 136]  # 0, <5000>

    # Assert that hwmon wasn't touched
    if has_hwmon:
        assert (tmp_path / "pwm1_enable").read_text() == "0"
        assert (tmp_path / "pwm1").read_text() == "0"
        assert (tmp_path / "pwm2_enable").read_text() == "0"
        assert (tmp_path / "pwm2").read_text() == "0"


@pytest.mark.parametrize("has_support", [False, True])
def test_octo_set_fixed_speeds_hwmon(mockOctoDevice, has_support, tmp_path):
    mockOctoDevice._hwmon = HwmonDevice("mock_module", tmp_path)

    if has_support:
        (tmp_path / "pwm1").write_text("0\n")
        (tmp_path / "pwm1_enable").write_text("0\n")
        (tmp_path / "pwm2").write_text("0\n")
        (tmp_path / "pwm2_enable").write_text("0\n")

    mockOctoDevice.set_fixed_speed("fan1", 84)
    mockOctoDevice.set_fixed_speed("fan2", 50)

    if has_support:
        assert (tmp_path / "pwm1_enable").read_text() == "1"
        assert (tmp_path / "pwm1").read_text() == "214"
        assert (tmp_path / "pwm2_enable").read_text() == "1"
        assert (tmp_path / "pwm2").read_text() == "127"
    else:
        # Assert fallback to direct access
        pump_report, fan_report = mockOctoDevice.device.sent

        assert pump_report.number == 3
        assert pump_report.data[0x59:0x5C] == [0, 32, 208]  # 0, <8400>
        assert fan_report.number == 3
        assert fan_report.data[0xAE:0xB1] == [0, 19, 136]  # 0, <5000>


def test_octo_speed_profiles_not_supported(mockOctoDevice):
    with pytest.raises(NotSupportedByDriver):
        mockOctoDevice.set_speed_profile("fan", None)


@pytest.fixture
def mockQuadroDevice():
    device = _MockQuadroDevice()
    dev = Aquacomputer(
        device,
        "Mock Aquacomputer Quadro",
        device_info=Aquacomputer._DEVICE_INFO[Aquacomputer._DEVICE_QUADRO],
    )

    dev.connect()
    return dev


class _MockQuadroDevice(MockHidapiDevice):
    def __init__(self):
        super().__init__(vendor_id=0x0C70, product_id=0xF00D)

        self.preload_read(Report(1, QUADRO_SAMPLE_STATUS_REPORT))
        self.preload_read(Report(3, QUADRO_SAMPLE_CONTROL_REPORT))
        self.preload_read(Report(3, QUADRO_SAMPLE_CONTROL_REPORT))

    def read(self, length):
        pre = super().read(length)
        if pre:
            return pre

        return Report(1, QUADRO_SAMPLE_STATUS_REPORT)


def test_quadro_connect(mockQuadroDevice):
    def mock_open():
        nonlocal opened
        opened = True

    mockQuadroDevice.device.open = mock_open
    opened = False

    with mockQuadroDevice.connect() as cm:
        assert cm == mockQuadroDevice
        assert opened


def test_quadro_initialize(mockQuadroDevice):
    init_result = mockQuadroDevice.initialize()

    # Verify firmware version
    assert init_result[0][1] == 1032

    # Verify serial number
    assert init_result[1][1] == "23410-65344"


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_quadro_get_status_directly(mockQuadroDevice, has_hwmon, direct_access):
    if has_hwmon:
        mockQuadroDevice._hwmon = HwmonDevice(None, None)

    got = mockQuadroDevice.get_status(direct_access=direct_access)

    expected = [
        ("Sensor 3", pytest.approx(16.17, 0.1), "°C"),
        ("Soft. Sensor 1", pytest.approx(23.9, 0.1), "°C"),
        ("Soft. Sensor 13", pytest.approx(50.0, 0.1), "°C"),
        ("Fan 1 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 1 power", pytest.approx(0, 0.1), "W"),
        ("Fan 1 voltage", pytest.approx(0, 0.1), "V"),
        ("Fan 1 current", pytest.approx(0, 0.1), "A"),
        ("Fan 2 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 2 power", pytest.approx(0, 0.1), "W"),
        ("Fan 2 voltage", pytest.approx(12.07, 0.1), "V"),
        ("Fan 2 current", pytest.approx(0, 0.1), "A"),
        ("Fan 3 speed", pytest.approx(356, 0.1), "rpm"),
        ("Fan 3 power", pytest.approx(0, 0.1), "W"),
        ("Fan 3 voltage", pytest.approx(12.07, 0.1), "V"),
        ("Fan 3 current", pytest.approx(0, 0.1), "A"),
        ("Fan 4 speed", pytest.approx(0, 0.1), "rpm"),
        ("Fan 4 power", pytest.approx(0, 0.1), "W"),
        ("Fan 4 voltage", pytest.approx(12.07, 0.1), "V"),
        ("Fan 4 current", pytest.approx(0, 0.1), "A"),
        ("Flow sensor", pytest.approx(0, 0.1), "dL/h"),
    ]

    assert sorted(got) == sorted(expected)


def test_quadro_get_status_from_hwmon(mockQuadroDevice, tmp_path):
    mockQuadroDevice._hwmon = HwmonDevice("mock_module", tmp_path)
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
    (tmp_path / "fan5_input").write_text("603\n")
    (tmp_path / "temp5_input").write_text("50000\n")  # Soft. Sensor 1 temperature
    (tmp_path / "temp6_input").write_text("60000\n")  # Soft. Sensor 2 temperature
    (tmp_path / "temp7_input").write_text("50000\n")  # Soft. Sensor 3 temperature
    (tmp_path / "temp8_input").write_text("50000\n")  # Soft. Sensor 4 temperature
    (tmp_path / "temp9_input").write_text("50000\n")  # Soft. Sensor 5 temperature
    (tmp_path / "temp10_input").write_text("50000\n")  # Soft. Sensor 6 temperature
    (tmp_path / "temp11_input").write_text("50000\n")  # Soft. Sensor 7 temperature
    (tmp_path / "temp12_input").write_text("50000\n")  # Soft. Sensor 8 temperature
    (tmp_path / "temp13_input").write_text("50000\n")  # Soft. Sensor 9 temperature
    (tmp_path / "temp14_input").write_text("50000\n")  # Soft. Sensor 10 temperature
    (tmp_path / "temp15_input").write_text("50000\n")  # Soft. Sensor 11 temperature
    (tmp_path / "temp16_input").write_text("50000\n")  # Soft. Sensor 12 temperature
    (tmp_path / "temp17_input").write_text("50000\n")  # Soft. Sensor 13 temperature
    (tmp_path / "temp18_input").write_text("50000\n")  # Soft. Sensor 14 temperature
    (tmp_path / "temp19_input").write_text("50000\n")  # Soft. Sensor 15 temperature
    (tmp_path / "temp20_input").write_text("50000\n")  # Soft. Sensor 16 temperature

    got = mockQuadroDevice.get_status()

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
        ("Flow sensor", pytest.approx(603, 0.1), "dL/h"),
        ("Soft. Sensor 1", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 2", pytest.approx(60, 0.1), "°C"),
        ("Soft. Sensor 3", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 4", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 5", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 6", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 7", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 8", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 9", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 10", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 11", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 12", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 13", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 14", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 15", pytest.approx(50, 0.1), "°C"),
        ("Soft. Sensor 16", pytest.approx(50, 0.1), "°C"),
    ]

    assert sorted(got) == sorted(expected)


@pytest.mark.parametrize("has_hwmon,direct_access", [(False, False), (True, True)])
def test_quadro_set_fixed_speeds_directly(mockQuadroDevice, has_hwmon, direct_access, tmp_path):
    """For both test cases only direct access should be used"""

    if has_hwmon:
        mockQuadroDevice._hwmon = HwmonDevice("mock_module", tmp_path)
        (tmp_path / "pwm1").write_text("0")
        (tmp_path / "pwm1_enable").write_text("0")
        (tmp_path / "pwm2").write_text("0")
        (tmp_path / "pwm2_enable").write_text("0")

    mockQuadroDevice.set_fixed_speed("fan1", 84, direct_access=direct_access)
    mockQuadroDevice.set_fixed_speed("fan2", 50, direct_access=direct_access)

    pump_report, fan_report = mockQuadroDevice.device.sent

    assert pump_report.number == 3
    assert pump_report.data[0x35:0x38] == [0, 32, 208]  # 0, <8400>
    assert fan_report.number == 3
    assert fan_report.data[0x8A:0x8D] == [0, 19, 136]  # 0, <5000>

    # Assert that hwmon wasn't touched
    if has_hwmon:
        assert (tmp_path / "pwm1_enable").read_text() == "0"
        assert (tmp_path / "pwm1").read_text() == "0"
        assert (tmp_path / "pwm2_enable").read_text() == "0"
        assert (tmp_path / "pwm2").read_text() == "0"


@pytest.mark.parametrize("has_support", [False, True])
def test_quadro_set_fixed_speeds_hwmon(mockQuadroDevice, has_support, tmp_path):
    mockQuadroDevice._hwmon = HwmonDevice("mock_module", tmp_path)

    if has_support:
        (tmp_path / "pwm1").write_text("0\n")
        (tmp_path / "pwm1_enable").write_text("0\n")
        (tmp_path / "pwm2").write_text("0\n")
        (tmp_path / "pwm2_enable").write_text("0\n")

    mockQuadroDevice.set_fixed_speed("fan1", 84)
    mockQuadroDevice.set_fixed_speed("fan2", 50)

    if has_support:
        assert (tmp_path / "pwm1_enable").read_text() == "1"
        assert (tmp_path / "pwm1").read_text() == "214"
        assert (tmp_path / "pwm2_enable").read_text() == "1"
        assert (tmp_path / "pwm2").read_text() == "127"
    else:
        # Assert fallback to direct access
        pump_report, fan_report = mockQuadroDevice.device.sent

        assert pump_report.number == 3
        assert pump_report.data[0x35:0x38] == [0, 32, 208]  # 0, <8400>
        assert fan_report.number == 3
        assert fan_report.data[0x8A:0x8D] == [0, 19, 136]  # 0, <5000>


def test_quadro_speed_profiles_not_supported(mockQuadroDevice):
    with pytest.raises(NotSupportedByDriver):
        mockQuadroDevice.set_speed_profile("fan", None)
