import os
from collections import deque, namedtuple

Report = namedtuple('Report', ['number', 'data'])


def noop(*args, **kwargs):
    return None


class MockRuntimeStorage:
    def __init__(self, key_prefixes):
        self._cache = {}

    def load(self, key, of_type=None, default=None):
        """Unstable API."""
        if key in self._cache:
            value = self._cache[key]
        else:
            value = None

        if value is None:
            return default
        elif of_type and not isinstance(value, of_type):
            return default
        else:
            return value

    def store(self, key, value):
        """Unstable API."""
        self._cache[key] = value
        return value


class MockHidapiDevice:
    def __init__(self, vendor_id=None, product_id=None, release_number=None,
                 serial_number=None, bus=None, address=None):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.release_number = release_number
        self.serial_number = serial_number
        self.bus = bus
        self.address = address
        self.port = None

        self.open = noop
        self.close = noop
        self.clear_enqueued_reports = noop

        self._read = deque()
        self.sent = list()

    def preload_read(self, report):
        self._read.append(report)

    def read(self, length):
        if self._read:
            number, data = self._read.popleft()
            if number:
                return [number] + list(data)[:length]
            else:
                return list(data)[:length]
        return None

    def write(self, data):
        data = bytes(data)  # ensure data is convertible to bytes
        self.sent.append(Report(data[0], list(data[1:])))
        return len(data)

    def get_feature_report(self, report_id, length):
        if self._read:
            try:
                report = next(filter(lambda x: x.number == report_id, self._read))
                number, data = report
                self._read.remove(report)
            except StopIteration:
                return None
            # length dictates the size of the buffer, and if it's not large
            # enough "ioctl (GFEATURE): Value too large for defined data type"
            # may happen on Linux; see:
            # https://github.com/liquidctl/liquidctl/issues/151#issuecomment-665119675
            assert length >= len(data) + 1, 'buffer not large enough for received report'
            return [number] + list(data)[:length]
        return None

    def send_feature_report(self, data):
        return self.write(data)


VirtualEeprom = namedtuple('VirtualEeprom', ['name', 'data'])


class VirtualSmbus:
    def __init__(self, address_count=256, register_count=256, name='i2c-99',
                 description='Virtual', parent_vendor=0xff01, parent_device=0xff02,
                 parent_subsystem_vendor=0xff10, parent_subsystem_device=0xff20,
                 parent_driver='virtual'):

        self._open = False
        self._data = [[0] * register_count for _ in range(address_count)]

        self.name = name
        self.description = description
        self.parent_vendor = parent_vendor
        self.parent_device = parent_device
        self.parent_subsystem_vendor = parent_subsystem_vendor
        self.parent_subsystem_device = parent_subsystem_device
        self.parent_driver = parent_driver

    def open(self):
        self._open = True

    def read_byte(self, address):
        if not self._open:
            raise OSError('closed')
        return self._data[address][0]

    def read_byte_data(self, address, register):
        if not self._open:
            raise OSError('closed')
        return self._data[address][register]

    def read_word_data(self, address, register):
        if not self._open:
            raise OSError('closed')
        return self._data[address][register]

    def read_block_data(self, address, register):
        if not self._open:
            raise OSError('closed')
        return self._data[address][register]

    def write_byte(self, address, value):
        if not self._open:
            raise OSError('closed')
        self._data[address][0] = value

    def write_byte_data(self, address, register, value):
        if not self._open:
            raise OSError('closed')
        self._data[address][register] = value

    def write_word_data(self, address, register, value):
        if not self._open:
            raise OSError('closed')
        self._data[address][register] = value

    def write_block_data(self, address, register, data):
        if not self._open:
            raise OSError('closed')
        self._data[address][register] = data

    def close(self):
        self._open = False

    def emulate_eeprom_at(self, address, name, data):
        self._data[address] = VirtualEeprom(name, data)  # hack

    def load_eeprom(self, address):
        return self._data[address]  # hack
