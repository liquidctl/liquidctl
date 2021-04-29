import pytest
from _testutils import VirtualBusDevice


def test_connects_and_disconnects_with_context_manager():
    dev = VirtualBusDevice()

    with pytest.raises(RuntimeError):
        with dev.connect():
            assert dev.connected
            raise RuntimeError()

    assert not dev.connected


def test_entering_the_runtime_context_does_not_call_connect():
    dev = VirtualBusDevice()

    with dev.connect(marker=True):
        # since __enter__ takes no arguments, if __enter__ calls connect it
        # will override dev.kwargs['connect'] with {}
        assert 'marker' in dev.call_args['connect'].kwargs
