import pytest
from multiprocessing import Process
import time
import os
import sys
from pathlib import Path

from liquidctl.keyval import _FilesystemBackend


def test_fs_backend_loads_from_fallback_dir(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')
    fb_dir = tmpdir.mkdir('fb_dir')

    fallback = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[fb_dir])
    fallback.store('key', 42)

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir, fb_dir])
    assert store.load('key') == 42

    store.store('key', -1)
    assert store.load('key') == -1
    assert fallback.load('key') == 42, 'fallback location was changed'


def test_fs_backend_handles_values_corupted_with_nulls(tmpdir, caplog):
    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    store.store('key', 42)
    key_file = Path(run_dir).joinpath('prefix', 'key')
    assert key_file.read_bytes() == b'42', 'unit test is unsound'

    key_file.write_bytes(b'\x00')
    val = store.load('key')

    assert val is None
    assert 'was corrupted' in caplog.text


def test_fs_backend_load_store_returns_old_and_new_values(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    assert store.load_store('key', lambda x: x + 1) == (42, 43)


def test_fs_backend_load_store_loads_from_fallback_dir(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')
    fb_dir = tmpdir.mkdir('fb_dir')

    fallback = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[fb_dir])
    fallback.store('key', 42)

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir, fb_dir])
    assert store.load_store('key', lambda x: x + 1) == (42, 43)

    assert fallback.load('key') == 42, 'fallback location was changed'


def test_fs_backend_load_store_is_atomic(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    ps = [
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .5)),
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .5)),
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .5)),
    ]

    start_time = time.monotonic()

    for p in ps:
        p.start()

    for p in ps:
        p.join()

    elapsed = (time.monotonic() - start_time)

    assert store.load('key') == 45
    assert elapsed >= .5 * len(ps)


def test_fs_backend_loads_honor_load_store_locking(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    ps = [
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .5)),
        Process(target=_fs_mp_check_key, args=(run_dir, 'prefix', 'key', 43)),
    ]

    ps[0].start()
    time.sleep(.1)
    ps[1].start()

    for p in ps:
        p.join()


def test_fs_backend_stores_honor_load_store_locking(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    ps = [
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .5)),
        Process(target=_fs_mp_store_key, args=(run_dir, 'prefix', 'key', -1)),
    ]

    start_time = time.monotonic()

    ps[0].start()
    time.sleep(.1)
    ps[1].start()

    # join second process first
    ps[1].join()

    elapsed = (time.monotonic() - start_time)
    assert elapsed >= .5

    ps[0].join()
    assert store.load('key') == -1


def _fs_mp_increment_key(run_dir, prefix, key, sleep):
    """Open a _FilesystemBackend and increment `key`.

    For the `multiprocessing` tests.

    Opens the storage on `run_dir` and with `prefix`.  Sleeps for `sleep`
    seconds within the increment closure.
    """

    def l(x):
        time.sleep(sleep)
        return x + 1

    store = _FilesystemBackend(key_prefixes=[prefix], runtime_dirs=[run_dir])
    store.load_store(key, l)


def _fs_mp_check_key(run_dir, prefix, key, expected):
    """Open a _FilesystemBackend and check `key` value against `expected`.

    For the `multiprocessing` tests.

    Opens the storage on `run_dir` and with `prefix`.
    """

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    assert store.load(key) == expected


def _fs_mp_store_key(run_dir, prefix, key, new_value):
    """Open a _FilesystemBackend and store `new_value` for `key`.

    For the `multiprocessing` tests.

    Opens the storage on `run_dir` and with `prefix`.
    """

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store(key, new_value)
