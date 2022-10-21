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


def test_modified_readme_example(capsys):
    from liquidctl import find_liquidctl_devices

    # Find all connected and supported devices.
    devices = find_liquidctl_devices(bus='virtual')  # readme: remove `bus` argument

    for dev in devices:

        # Connect to the device. In this example we use a context manager, but
        # the connection can also be manually managed. The context manager
        # automatically calls `disconnect`; when managing the connection
        # manually, `disconnect` must eventually be called, even if an
        # exception is raised.
        with dev.connect():
            print(f'{dev.description} at {dev.bus}:{dev.address}:')

            # Devices should be initialized after every boot. In this example
            # we assume that this has not been done before.
            print('- initialize')
            init_status = dev.initialize()

            # Print all data returned by `initialize`.
            if init_status:
                for key, value, unit in init_status:
                    print(f'- {key}: {value} {unit}')

            # Get regular status information from the device.
            status = dev.get_status()

            # Print all data returned by `get_status`.
            print('- get status')
            for key, value, unit in status:
                print(f'- {key}: {value} {unit}')

            # For a particular device, set the pump LEDs to red.
            if 'Virtual Bus Device' in dev.description: # readme: replace with 'Kraken'
                print('- set pump to radical red')
                radical_red = [0xff, 0x35, 0x5e]
                dev.set_color(channel='pump', mode='fixed', colors=[radical_red])


    # end of modified example; check that it more or less did what it should

    out, _ = capsys.readouterr()
    assert 'Virtual Bus Device (experimental) at virtual:virtual_address:' in out
    assert 'initialize' in out
    assert 'Firmware version: 3.14.16' in out
    assert 'get status' in out
    assert 'Temperature: 30.4 °C' in out
    assert 'set pump to radical red' in out
