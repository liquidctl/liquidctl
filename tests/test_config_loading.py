import pytest
import sys
import os

from liquidctl.config.load import get_config_files, filter_config_files


windows_only = pytest.mark.skipif(sys.platform != 'win32', reason="This test should only run on windows")
mac_only = pytest.mark.skipif(sys.platform != 'darwin', reason="This test should only run on macos")
linux_only = pytest.mark.skipif(sys.platform != 'linux', reason="This test should only run on linux")
other_only = pytest.mark.skipif(sys.platform != 'cygwin' and sys.platform != 'aix', reason="This test should only run on any other system")


@mac_only
def test_load_mac_no_file(monkeypatch):
    monkeypatch.setenv('HOME', 'user')
    res = get_config_files()

    assert len(res) == 2
    assert 'user/Library/Application Support/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@mac_only
def test_load_mac_file(monkeypatch):
    monkeypatch.setenv('HOME', 'user')
    res = get_config_files('abcd.toml')

    assert len(res) == 3
    assert 'abcd.toml' in res
    assert 'user/Library/Application Support/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@windows_only
def test_load_windows_no_file(monkeypatch):
    monkeypatch.setenv('APPDATA', 'user')
    res = get_config_files()

    assert len(res) == 1
    assert 'user/liquidctl/config.toml' in res

@windows_only
def test_load_windows_file(monkeypatch):
    monkeypatch.setenv('APPDATA', 'user')
    res = get_config_files('abcd.toml')

    assert len(res) == 2
    assert 'abcd.toml' in res
    assert 'user/liquidctl/config.toml' in res

@linux_only
def test_load_linux_no_file_specified_no_xdg_config_home(monkeypatch):

    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setenv('XDG_CONFIG_DIRS', 'var')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files()

    assert len(res) == 3
    assert 'var/liquidctl/config.toml' in res
    assert 'user/.config/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@linux_only
def test_load_linux_no_file_specified_no_xdg_config_dir(monkeypatch):

    monkeypatch.delenv('XDG_CONFIG_DIRS', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', '/home/bobfrank/.secret')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files()

    assert len(res) == 3
    assert '/home/bobfrank/.secret/liquidctl/config.toml' in res
    assert 'user/.config/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@linux_only
def test_load_linux_no_file_specified_no_xdg_config_either(monkeypatch):

    monkeypatch.delenv('XDG_CONFIG_DIRS', raising=False)
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setenv('HOME', 'name')

    res = get_config_files()

    assert len(res) == 2
    assert 'name/.config/liquidctl/config.toml' in res
    assert 'name/.liquidctl.toml' in res

@linux_only
def test_load_linux_no_file_specified_both_xdg_config(monkeypatch):

    monkeypatch.setenv('XDG_CONFIG_DIRS', 'var')
    monkeypatch.setenv('XDG_CONFIG_HOME', '/home/bobfrank/.secret')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files()

    assert len(res) == 4
    assert 'var/liquidctl/config.toml' in res
    assert '/home/bobfrank/.secret/liquidctl/config.toml' in res
    assert 'user/.config/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@linux_only
def test_load_linux_file_specified_both_xdg_config(monkeypatch):

    monkeypatch.setenv('XDG_CONFIG_DIRS', 'var')
    monkeypatch.setenv('XDG_CONFIG_HOME', '/home/bobfrank/.secret')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files('abcd.toml')

    assert len(res) == 5

    assert 'abcd.toml' in res
    assert 'var/liquidctl/config.toml' in res
    assert '/home/bobfrank/.secret/liquidctl/config.toml' in res
    assert 'user/.config/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@other_only
def test_load_other_no_file(monkeypatch):
    monkeypatch.setenv('HOME', 'user')
    res = get_config_files()

    assert len(res) == 1
    assert 'user/.liquidctl.toml' in res

@other_only
def test_load_other_file(monkeypatch):
    monkeypatch.setenv('HOME', 'user')
    res = get_config_files('abcd.toml')

    assert len(res) == 2
    assert 'abcd.toml' in res
    assert 'user/.liquidctl.toml' in res

def test_config_filtering_none():
    assert filter_config_files() is None

def test_config_filtering_empty():
    assert filter_config_files([]) is None

def test_config_filtering_existing_file(tmpdir):
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")

    assert filter_config_files([p.realpath()]) == p.realpath()

def test_config_filtering_existing_file_after_fake(tmpdir):
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")

    assert filter_config_files(['fake', p.realpath()]) == p.realpath()

def test_config_filtering_existing_file_before_fake(tmpdir):
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")

    assert filter_config_files([p.realpath(), 'fake']) == p.realpath()

def test_config_filtering_existing_file_multiple(tmpdir):
    p = tmpdir.mkdir("sub").join("hello.txt")
    p2 = tmpdir.join("test2.txt")
    p.write("content")
    p2.write("more content")

    assert filter_config_files([p.realpath(), p2.realpath()]) == p.realpath()
    assert filter_config_files([p2.realpath(), p.realpath()]) == p2.realpath()

def test_config_filtering_existing_file_ignore(tmpdir):
    p = tmpdir.mkdir("sub").join("hello.txt")
    p.write("content")

    assert filter_config_files([p.realpath()], ignore_config=True) == None

def test_config_filtering_fake_ignore():
    assert filter_config_files(['abc'], ignore_config=True) == None
