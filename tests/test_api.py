import pytest
from liquidctl.driver.base import BaseDriver


class Virtual(BaseDriver):
    def __init__(self, **kwargs):
        self.kwargs = dict()
        self.kwargs['__init__'] = kwargs
        self.connected = False

    def connect(self, **kwargs):
        self.kwargs['connect'] = kwargs
        self.connected = True
        return self

    def disconnect(self, **kwargs):
        self.kwargs['disconnect'] = kwargs
        self.connected = False


def test_connects_and_disconnects_with_context_manager():
    dev = Virtual()

    with pytest.raises(RuntimeError):
        with dev.connect():
            assert dev.connected
            raise RuntimeError()

    assert not dev.connected


def test_entering_the_runtime_context_does_not_call_connect():
    dev = Virtual()

    with dev.connect(marker=True):
        # since __enter__ takes no arguments, if __enter__ calls connect it
        # will override dev.kwargs['connect'] with {}
        assert 'marker' in dev.kwargs['connect']
