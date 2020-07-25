import unittest

class Pre14NamesTestCase(unittest.TestCase):
    def test_old_module_names(self):
        import liquidctl.driver.asetek
        import liquidctl.driver.corsair_hid_psu
        import liquidctl.driver.kraken_two
        import liquidctl.driver.nzxt_smart_device
        import liquidctl.driver.seasonic

    def test_old_driver_names(self):
        from liquidctl.driver.asetek import AsetekDriver
        from liquidctl.driver.asetek import LegacyAsetekDriver
        from liquidctl.driver.asetek import CorsairAsetekDriver
        from liquidctl.driver.corsair_hid_psu import CorsairHidPsuDriver
        from liquidctl.driver.kraken_two import KrakenTwoDriver
        from liquidctl.driver.nzxt_smart_device import SmartDeviceDriver
        from liquidctl.driver.nzxt_smart_device import SmartDeviceV2Driver
        from liquidctl.driver.seasonic import SeasonicEDriver
