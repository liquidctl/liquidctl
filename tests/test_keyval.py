import os
import pytest
import sys
import time
from multiprocessing import Process
from pathlib import Path

from liquidctl.keyval import RuntimeStorage, _FilesystemBackend


@pytest.fixture
def tmpstore(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')
    prefixes = ['prefix']

    backend = _FilesystemBackend(key_prefixes=prefixes, runtime_dirs=[run_dir])
    return RuntimeStorage(prefixes, backend=backend)


def test_loads_and_stores(tmpstore):
    assert tmpstore.load('key') is None
    assert tmpstore.load('key', default=42) == 42

    tmpstore.store('key', '42')

    assert tmpstore.load('key') == '42'
    assert tmpstore.load('key', of_type=int) is None


def test_updates_with_load_store(tmpstore):
    assert tmpstore.load_store('key', lambda x: x) == (None, None)
    assert tmpstore.load_store('key', lambda x: x, default=42) == (None, 42)
    assert tmpstore.load_store('key', lambda x: str(x)) == (42, '42')
    assert tmpstore.load_store('key', lambda x: x, of_type=int) == ('42', None)


def test_fs_backend_stores_truncate_appropriately(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    # use a separate reader to prevent caching from masking issues
    writer = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    reader = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    writer.store('key', 42)
    assert reader.load('key') == 42

    writer.store('key', 1)
    assert reader.load('key') == 1

    writer.load_store('key', lambda _: 42)
    assert reader.load('key') == 42

    writer.load_store('key', lambda _: 1)
    assert reader.load('key') == 1


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

    assert store.load_store('key', lambda _: 42) == (None, 42)
    assert store.load_store('key', lambda x: x + 1) == (42, 43)


def test_fs_backend_load_store_loads_from_fallback_dir(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')
    fb_dir = tmpdir.mkdir('fb_dir')

    fallback = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[fb_dir])
    fallback.store('key', 42)

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir, fb_dir])
    assert store.load_store('key', lambda x: x + 1) == (42, 43)

    assert fallback.load('key') == 42, 'content in fallback location changed'


def test_fs_backend_load_store_loads_from_fallback_dir_that_is_symlink(tmpdir):
    # should deadlock if there is a problem with the lock type or with the
    # handling of fallback paths that point to the same principal/write
    # directory

    run_dir = tmpdir.mkdir('run_dir')
    fb_dir = os.path.join(run_dir, 'symlink')
    os.symlink(run_dir, fb_dir, target_is_directory=True)

    # don't store any initial value so that the fallback location is checked

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir, fb_dir])
    assert store.load_store('key', lambda x: 42) == (None, 42)

    fallback = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[fb_dir])
    assert fallback.load('key') == 42, 'content in fallback symlink did not change'


def test_fs_backend_load_store_is_atomic(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    ps = [
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .2)),
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .2)),
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .2)),
    ]

    start_time = time.monotonic()

    for p in ps:
        p.start()

    for p in ps:
        p.join()

    elapsed = (time.monotonic() - start_time)

    assert store.load('key') == 45
    assert elapsed >= .2 * len(ps)


def test_fs_backend_loads_honor_load_store_locking(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    ps = [
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .2)),
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
        Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', .2)),
        Process(target=_fs_mp_store_key, args=(run_dir, 'prefix', 'key', -1)),
    ]

    start_time = time.monotonic()

    ps[0].start()
    time.sleep(.1)
    ps[1].start()

    # join second process first
    ps[1].join()

    elapsed = (time.monotonic() - start_time)
    assert elapsed >= .2

    ps[0].join()
    assert store.load('key') == -1


def test_fs_backend_releases_locks(tmpdir):
    # should deadlock if any method does not properly release its lock

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    def incr_from_other_process():
        other = Process(target=_fs_mp_increment_key, args=(run_dir, 'prefix', 'key', 0.))
        other.start()
        other.join()

    store.store('key', 42)
    incr_from_other_process()
    assert store.load('key') == 43

    store.load_store('key', lambda _: -1)
    incr_from_other_process()
    assert store.load('key') == 0

    incr_from_other_process()
    assert store.load('key') == 1


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
