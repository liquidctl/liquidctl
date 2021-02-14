import pytest
from multiprocessing import Process
import time
import os
import sys
from pathlib import Path

from liquidctl.keyval import _FilesystemBackend


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


def test_fs_backend_load_store(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    p1 = Process(target=_mp_increment_key, args=(run_dir, 'prefix', 'key', .5))
    p2 = Process(target=_mp_increment_key, args=(run_dir, 'prefix', 'key', .5))
    p3 = Process(target=_mp_increment_key, args=(run_dir, 'prefix', 'key', .5))

    startTime = time.time()
    p1.start()
    p2.start()
    p3.start()

    p1.join()
    p2.join()
    p3.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    val = store.load('key')

    assert val == 45
    assert diffTime == pytest.approx(1.5, abs=.25)   # check that the sleeps add up


@pytest.mark.parametrize('key', [
    'key1', 'key-value', 'new_key', 'ob1', 'abracadabra'
    ])
def test_fs_backend_lock_file(tmpdir, key):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    file = store._lock_file(key)
    assert os.path.basename(file) == f'{key}.lock'


def test_fs_backend_shared_lock_locked(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    with store._shared_lock('key', locked=True):
        assert not os.path.exists(store._lock_file('key'))


def test_fs_backend_exclusive_lock_locked(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    with store._exclusive_lock('key', locked=True):
        assert not os.path.exists(store._lock_file('key'))


def test_fs_backend_shared_lock(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    with store._shared_lock('key'):
        assert os.path.exists(store._lock_file('key'))

    assert os.path.exists(store._lock_file('key'))


def test_fs_backend_exclusive_lock(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    with store._exclusive_lock('key'):
        assert os.path.exists(store._lock_file('key'))

    assert os.path.exists(store._lock_file('key'))


def test_fs_backend_share_lock(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    p1 = Process(target=_mp_shared_sleep, args=(run_dir, 'prefix', 'key', .5))
    p2 = Process(target=_mp_shared_sleep, args=(run_dir, 'prefix', 'key', .5))
    p3 = Process(target=_mp_shared_sleep, args=(run_dir, 'prefix', 'key', .5))

    startTime = time.time()
    p1.start()
    p2.start()
    p3.start()

    p1.join()
    p2.join()
    p3.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    if sys.platform == 'win32':
        # no shared locks on windows
        assert diffTime == pytest.approx(1.5, abs=.25)
    else:
        assert diffTime == pytest.approx(.5, abs=.25)


def test_fs_backend_exclusive_lock(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    p1 = Process(target=_mp_exclusive_sleep, args=(run_dir, 'prefix', 'key', .5))
    p2 = Process(target=_mp_exclusive_sleep, args=(run_dir, 'prefix', 'key', .5))

    startTime = time.time()
    p1.start()
    p2.start()

    p1.join()
    p2.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    assert diffTime == pytest.approx(1, abs=.25)


def test_fs_backend_mixed_lock_exclusive_first(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    p1 = Process(target=_mp_exclusive_sleep, args=(run_dir, 'prefix', 'key', .5))
    p2 = Process(target=_mp_shared_sleep, args=(run_dir, 'prefix', 'key', .5))
    p3 = Process(target=_mp_shared_sleep, args=(run_dir, 'prefix', 'key', .5))

    startTime = time.time()
    p1.start()
    time.sleep(0.1)
    p2.start()
    p3.start()

    p1.join()
    p2.join()
    p3.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    if sys.platform == 'win32':
        # no shared locks on windows
        assert diffTime == pytest.approx(1.5, abs=.25)
    else:
        assert diffTime == pytest.approx(1.0, abs=.25)


def test_fs_backend_mixed_lock_shared_first(tmpdir):
    run_dir = tmpdir.mkdir('run_dir')

    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])
    store.store('key', 42)

    p1 = Process(target=_mp_shared_sleep, args=(run_dir, 'prefix', 'key', .5))
    p2 = Process(target=_mp_shared_sleep, args=(run_dir, 'prefix', 'key', .5))
    p3 = Process(target=_mp_exclusive_sleep, args=(run_dir, 'prefix', 'key', .5))

    startTime = time.time()
    p1.start()
    p2.start()
    time.sleep(0.1)
    p3.start()

    p1.join()
    p2.join()
    p3.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    if sys.platform == 'win32':
        # no shared locks on windows
        assert diffTime == pytest.approx(1.5, abs=.25)
    else:
        assert diffTime == pytest.approx(1.0, abs=.25)


def _mp_increment_key(run_dir, prefix, key, sleep):
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


def _mp_exclusive_sleep(run_dir, prefix, key, sleep):
    """Open a _FilesystemBackend and sleep on `key` holding a exclusive lock.

    For the `multiprocessing` tests.

    Opens the storage on `run_dir` and with `prefix`.  Sleeps for `sleep`
    seconds.
    """

    store = _FilesystemBackend(key_prefixes=[prefix], runtime_dirs=[run_dir])

    with store._exclusive_lock(key):
        time.sleep(sleep)


def _mp_shared_sleep(run_dir, prefix, key, sleep):
    """Open a _FilesystemBackend and sleep on `key` holding a shared lock.

    For the `multiprocessing` tests.

    Opens the storage on `run_dir` and with `prefix`.  Sleeps for `sleep`
    seconds.
    """

    store = _FilesystemBackend(key_prefixes=[prefix], runtime_dirs=[run_dir])

    with store._shared_lock(key):
        time.sleep(sleep)
