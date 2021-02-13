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


# this is the process that will test the load store code
def inc_proccess(store):

    def l(x):
        time.sleep(2)
        return x+1

    store.load_store('key', l)


def test_fs_backend_load_store(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    store.store('key', 42)

    p1 = Process(target=inc_proccess, args=(store,))
    p2 = Process(target=inc_proccess, args=(store,))
    p3 = Process(target=inc_proccess, args=(store,))
    p4 = Process(target=inc_proccess, args=(store,))

    startTime = time.time()
    p1.start()
    p2.start()
    p3.start()
    p4.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    val = store.load('key')

    assert val == 46
    assert diffTime == pytest.approx(8, rel=1)   # check that the sleeps add up


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


# this is the process that will test if multiple proccesses can share a lock
def shared_lock_sleep(store):

    with store._shared_lock('key'):
        time.sleep(2)

# this is the process that will test if multiple proccesses can share a lock def shared_lock_sleep(store):
def exclusive_lock_sleep(store):

    with store._exclusive_lock('key'):
        time.sleep(2)


def test_fs_backend_share_lock(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    store.store('key', 42)

    p1 = Process(target=shared_lock_sleep, args=(store,))
    p2 = Process(target=shared_lock_sleep, args=(store,))
    p3 = Process(target=shared_lock_sleep, args=(store,))
    p4 = Process(target=shared_lock_sleep, args=(store,))

    startTime = time.time()
    p1.start()
    p2.start()
    p3.start()
    p4.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()

    endTime = time.time()
    diffTime = (endTime-startTime)


    # no shared locks on windows
    if sys.platform == 'win32':
        assert diffTime == pytest.approx(8, rel=1)   # check that the sleeps add up
    elif sys.platform == 'dawrin':
        diffTime == pytest.approx(8, rel=1)
    else:
        assert diffTime == pytest.approx(2, rel=1)   # check that the sleeps add up


def test_fs_backend_exclusive_lock(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    store.store('key', 42)

    p1 = Process(target=exclusive_lock_sleep, args=(store,))
    p2 = Process(target=exclusive_lock_sleep, args=(store,))
    p3 = Process(target=exclusive_lock_sleep, args=(store,))
    p4 = Process(target=exclusive_lock_sleep, args=(store,))

    startTime = time.time()
    p1.start()
    p2.start()
    p3.start()
    p4.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    assert diffTime == pytest.approx(8, rel=1)   # check that the sleeps add up


def test_fs_backend_mixed_lock_exclusive_first(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    store.store('key', 42)

    p1 = Process(target=exclusive_lock_sleep, args=(store,))
    p2 = Process(target=shared_lock_sleep, args=(store,))
    p3 = Process(target=shared_lock_sleep, args=(store,))
    p4 = Process(target=shared_lock_sleep, args=(store,))

    startTime = time.time()
    p1.start()
    time.sleep(0.1)
    p2.start()
    p3.start()
    p4.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    # no shared locks on windows
    if sys.platform == 'win32':
        assert diffTime == pytest.approx(8.1, rel=1)   # check that the sleeps add up
    elif sys.platform == 'dawrin':
        diffTime == pytest.approx(8.1, rel=1)
    else:
        assert diffTime == pytest.approx(4.1, rel=1)   # check that the sleeps add up


def test_fs_backend_mixed_lock_shared_first(tmpdir):

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    store.store('key', 42)

    p1 = Process(target=shared_lock_sleep, args=(store,))
    p2 = Process(target=shared_lock_sleep, args=(store,))
    p3 = Process(target=exclusive_lock_sleep, args=(store,))
    p4 = Process(target=shared_lock_sleep, args=(store,))

    startTime = time.time()
    p1.start()
    time.sleep(0.1)
    p2.start()
    p3.start()
    time.sleep(0.1)
    p4.start()

    p1.join()
    p2.join()
    p3.join()
    p4.join()

    endTime = time.time()
    diffTime = (endTime-startTime)

    # no shared locks on windows
    if sys.platform == 'win32':
        assert diffTime == pytest.approx(8.2, rel=1)   # check that the sleeps add up
    elif sys.platform == 'dawrin':
        diffTime == pytest.approx(8.2, rel=1)
    else:
        assert diffTime == pytest.approx(4.2, rel=1)  # check that the sleeps add up
