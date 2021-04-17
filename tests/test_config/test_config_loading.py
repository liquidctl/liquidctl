import pytest
import sys
import os

from liquidctl.config.load import get_config_files, filter_config_files


windows_only = pytest.mark.skipif(sys.platform != 'win32', reason="This test should only run on windows")
not_windows = pytest.mark.skipif(sys.platform == 'win32', reason="This test should not run on windows")


@windows_only
def test_load_windows_no_file(monkeypatch):
    monkeypatch.setenv('APPDATA', 'AppData')
    monkeypatch.setenv('LOCALAPPDATA', 'AppData\\Local')
    monkeypatch.setenv('PROGRAMDATA', 'ProgramData')
    res = get_config_files()

    assert len(res) == 3
    assert 'AppData\\liquidctl\\config.toml' in res
    assert 'AppData\\Local\\liquidctl\\config.toml' in res
    assert 'ProgramData\\liquidctl\\config.toml' in res

@windows_only
def test_load_windows_file(monkeypatch):
    monkeypatch.setenv('APPDATA', 'AppData')
    monkeypatch.setenv('LOCALAPPDATA', 'AppData\\Local')
    monkeypatch.setenv('PROGRAMDATA', 'ProgramData')
    res = get_config_files('abcd.toml')

    assert len(res) == 4
    assert 'abcd.toml' in res
    assert 'AppData\\liquidctl\\config.toml' in res
    assert 'AppData\\Local\\liquidctl\\config.toml' in res
    assert 'ProgramData\\liquidctl\\config.toml' in res

@not_windows
def test_load_linux_no_file_specified_no_xdg_config_home(monkeypatch):

    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setenv('XDG_CONFIG_DIRS', 'var')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files()

    assert len(res) == 3
    assert 'var/liquidctl/config.toml' in res
    assert 'user/.config/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@not_windows
def test_load_linux_no_file_specified_no_xdg_config_dir(monkeypatch):

    monkeypatch.delenv('XDG_CONFIG_DIRS', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', '/home/bobfrank/.secret')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files()

    assert len(res) == 3
    assert '/home/bobfrank/.secret/liquidctl/config.toml' in res
    assert '/etc/xdg/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@not_windows
def test_load_linux_no_file_specified_no_xdg_config_either(monkeypatch):

    monkeypatch.delenv('XDG_CONFIG_DIRS', raising=False)
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setenv('HOME', 'name')

    res = get_config_files()

    assert len(res) == 3
    assert 'name/.config/liquidctl/config.toml' in res
    assert '/etc/xdg/liquidctl/config.toml' in res
    assert 'name/.liquidctl.toml' in res

@not_windows
def test_load_linux_no_file_specified_both_xdg_config(monkeypatch):

    monkeypatch.setenv('XDG_CONFIG_DIRS', 'var')
    monkeypatch.setenv('XDG_CONFIG_HOME', '/home/bobfrank/.secret')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files()

    assert len(res) == 3
    assert 'var/liquidctl/config.toml' in res
    assert '/home/bobfrank/.secret/liquidctl/config.toml' in res
    assert 'user/.liquidctl.toml' in res

@not_windows
def test_load_linux_file_specified_both_xdg_config(monkeypatch):

    monkeypatch.setenv('XDG_CONFIG_DIRS', 'var')
    monkeypatch.setenv('XDG_CONFIG_HOME', '/home/bobfrank/.secret')
    monkeypatch.setenv('HOME', 'user')

    res = get_config_files('abcd.toml')

    assert len(res) == 4

    assert 'abcd.toml' in res
    assert 'var/liquidctl/config.toml' in res
    assert '/home/bobfrank/.secret/liquidctl/config.toml' in res
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
