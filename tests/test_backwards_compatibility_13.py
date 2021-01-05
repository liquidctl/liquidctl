import pytest


def test_pre14_old_module_names():
    import liquidctl.driver.asetek
    import liquidctl.driver.corsair_hid_psu
    import liquidctl.driver.kraken_two
    import liquidctl.driver.nzxt_smart_device
    import liquidctl.driver.seasonic


def test_pre14_old_driver_names():
    from liquidctl.driver.asetek import AsetekDriver
    from liquidctl.driver.asetek import LegacyAsetekDriver
    from liquidctl.driver.asetek import CorsairAsetekDriver
    from liquidctl.driver.corsair_hid_psu import CorsairHidPsuDriver
    from liquidctl.driver.kraken_two import KrakenTwoDriver
    from liquidctl.driver.nzxt_smart_device import SmartDeviceDriver
    from liquidctl.driver.nzxt_smart_device import SmartDeviceV2Driver
    from liquidctl.driver.seasonic import SeasonicEDriver
