from pathlib import Path

import pytest


def test_fs_backend_handles_values_corupted_with_nulls(tmpdir, caplog):
    from liquidctl.keyval import _FilesystemBackend

    run_dir = tmpdir.mkdir('run_dir')
    store = _FilesystemBackend(key_prefixes=['prefix'], runtime_dirs=[run_dir])

    store.store('key', 42)
    key_file = Path(run_dir).joinpath('prefix', 'key')
    assert key_file.read_bytes() == b'42', 'unit test is unsound'

    key_file.write_bytes(b'\x00')
    val = store.load('key')

    assert val is None
    assert 'was corrupted' in caplog.text
