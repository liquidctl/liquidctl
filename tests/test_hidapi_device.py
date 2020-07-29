from pytest import fixture
from liquidctl.driver.usb import HidapiDevice


class _mockhidapi:
    @staticmethod
    def device():
        return _mockdevice()


class _mockdevice:
    pass


_SAMPLE_HID_INFO = {
    'path': b'path',
    'vendor_id': 0xf001,
    'product_id': 0xf002,
    'serial_number': 'serial number',
    'release_number': 0xf003,
    'manufacturer_string': 'manufacturer',
    'product_string': 'product',
    'usage_page': 0xf004,
    'usage': 0xf005,
    'interface_number': 0x01,
}


@fixture
def dev():
    return HidapiDevice(_mockhidapi, _SAMPLE_HID_INFO)


def test_opens(dev, monkeypatch):
    opened = False

    def _open_path(path):
        assert isinstance(path, bytes)
        nonlocal opened
        opened = True

    monkeypatch.setattr(dev.hiddev, 'open_path', _open_path, raising=False)
    dev.open()
    assert opened


def test_closes(dev, monkeypatch):
    opened = True

    def _close():
        nonlocal opened
        opened = False

    monkeypatch.setattr(dev.hiddev, 'close', _close, raising=False)
    dev.close()
    assert not opened


def test_can_clear_enqueued_reports(dev, monkeypatch):
    queue = [[1], [2], [3]]

    def _set_nonblocking(v):
        assert isinstance(v, int)
        return 0

    def _read(max_length, timeout_ms=0):
        assert isinstance(max_length, int)
        assert isinstance(timeout_ms, int)
        assert timeout_ms == 0, 'use hid_read'
        nonlocal queue
        if queue:
            return queue.pop()
        return []

    monkeypatch.setattr(dev.hiddev, 'set_nonblocking', _set_nonblocking, raising=False)
    monkeypatch.setattr(dev.hiddev, 'read', _read, raising=False)
    dev.clear_enqueued_reports()
    assert not queue


def test_can_clear_enqueued_reports_without_nonblocking(dev, monkeypatch):
    queue = [[1], [2], [3]]

    def _set_nonblocking(v):
        assert isinstance(v, int)
        return -1

    def _read(max_length, timeout_ms=0):
        assert isinstance(max_length, int)
        assert isinstance(timeout_ms, int)
        assert timeout_ms > 0, 'use hid_read_timeout'
        nonlocal queue
        if queue:
            return queue.pop()
        return []

    monkeypatch.setattr(dev.hiddev, 'set_nonblocking', _set_nonblocking, raising=False)
    monkeypatch.setattr(dev.hiddev, 'read', _read, raising=False)
    dev.clear_enqueued_reports()
    assert not queue


def test_reads(dev, monkeypatch):
    def _set_nonblocking(v):
        assert isinstance(v, int)
        return 0

    def _read(max_length, timeout_ms=0):
        assert isinstance(max_length, int)
        assert isinstance(timeout_ms, int)
        assert timeout_ms == 0, 'use hid_read'
        return [0xff] + [0]*(max_length - 1)  # report ID is part of max_length *if present*

    monkeypatch.setattr(dev.hiddev, 'set_nonblocking', _set_nonblocking, raising=False)
    monkeypatch.setattr(dev.hiddev, 'read', _read, raising=False)
    assert dev.read(5) == [0xff, 0, 0, 0, 0]


def test_can_write(dev, monkeypatch):
    def _write(buff):
        buff = bytes(buff)
        return len(buff)  # report ID is (always) part of returned length

    monkeypatch.setattr(dev.hiddev, 'write', _write, raising=False)
    assert dev.write([0xff, 42]) == 2
    assert dev.write([0, 42]) == 2
    assert dev.write(b'foo') == 3


def test_gets_feature_report(dev, monkeypatch):
    def _get(report_num, max_length):
        assert isinstance(report_num, int)
        assert isinstance(max_length, int)
        return [report_num] + [0]*(max_length - 1)  # report ID is (always) part of max_length

    monkeypatch.setattr(dev.hiddev, 'get_feature_report', _get, raising=False)
    assert dev.get_feature_report(0xff, 3) == [0xff, 0, 0]
    assert dev.get_feature_report(0, 3) == [0, 0, 0]


def test_can_send_feature_report(dev, monkeypatch):
    def _send(buff):
        buff = bytes(buff)
        return len(buff)  # report ID is (always) part of returned length

    monkeypatch.setattr(dev.hiddev, 'send_feature_report', _send, raising=False)
    assert dev.send_feature_report([0xff, 42]) == 2
    assert dev.send_feature_report([0, 42]) == 2
    assert dev.send_feature_report(b'foo') == 3


def test_exposes_unified_properties(dev):
    assert dev.vendor_id == 0xf001
    assert dev.product_id == 0xf002
    assert dev.release_number == 0xf003
    assert dev.serial_number == 'serial number'
    assert dev.bus == 'hid'
    assert dev.address == 'path'
    assert dev.port is None
