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

    first = True

    # find all connected and supported devices on pseudo bus 'virtual'
    devices = find_liquidctl_devices(bus='virtual')

    for dev in devices:

        # connect to the device (here a context manager is used, but the
        # connection can also be manually managed)
        with dev.connect():
            print(f'{dev.description} at {dev.bus}:{dev.address}:')

            # devices should be initialized after every boot (here we assume
            # this has not been done before)
            init_status = dev.initialize()

            # print all data returned by initialize()
            if init_status:
                for key, value, unit in init_status:
                    print(f'{key}: {value} {unit}')

            # get regular status information from the device
            status = dev.get_status()

            # print all data returned by get_status()
            for key, value, unit in status:
                print(f'{key}: {value} {unit}')

            # for a particular device, set the pump LEDs to red
            if 'Virtual Bus Device' in dev.description:
                print('setting pump to radical red')
                radical_red = [0xff, 0x35, 0x5e]
                dev.set_color(channel='pump', mode='fixed', colors=[radical_red])

        # the context manager took care of automatically calling disconnect();
        # when manually managing the connection, disconnect() must be called at
        # some point even if an exception is raised

        if first:
            first = False
            print()  # add a blank line between each device

    # end of modified example; check that it more or less did what it should

    out, _ = capsys.readouterr()
    assert 'Virtual Bus Device (experimental) at virtual:virtual_address:' in out
    assert 'Firmware version: 3.14.16' in out
    assert 'Temperature: 30.4 °C' in out
    assert 'setting pump to radical red' in out
