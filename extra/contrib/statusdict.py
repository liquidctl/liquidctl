import collections.abc


class StatusDict(collections.abc.Mapping):
    """Wrap a `get_status()` list in a dict-like interface.

    Don't use for now, unstable API and very inefficient.
    """

    __slots__ = ["inner"]

    def __init__(self, status):
        """Construct a StatusDict from a `status` list.

        Intended to be used with the output from `<device>.get_status()`.
        Thus, and unlike normal dictionaries, mutation is not allowed.

        `status` should be a list of `(key, value, unit)` tuples, where all
        keys are unique.  The `status` list should not be mutated while wrapped
        by a `StatusDict`.
        """

        self.inner = status

    def list(self):
        """Return a list of all the keys.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> statusdict.list()
        ['Temperature', 'Fan speed']
        """

        return [key for key, _, _ in self.inner]

    def __len__(self):
        """Return the number of items.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> len(statusdict)
        2
        """

        return len(self.inner)

    def __getitem__(self, key):
        """Return the item `(value, unit)` with key `key`.

        Raises a `KeyError` if key is not in the map.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> statusdict['Fan speed']
        (1435, 'rpm')
        >>> statusdict['Pump speed']
        Traceback (most recent call last):
            ...
        KeyError: 'Pump speed'
        """

        for _key, value, unit in self.inner:
            if _key == key:
                return (value, unit)
        raise KeyError(key)

    def get(self, key, default=None):
        """Return the item `(value, unit)` for `key` or `default`.

        If `default` is not given, it defaults to `None`, so that this method
        never raises a `KeyError`.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> statusdict.get('Fan speed')
        (1435, 'rpm')
        >>> statusdict.get('Pump speed') is None
        True
        >>> statusdict.get('Pump speed', default='missing')
        'missing'
        """

        for _key, value, unit in self.inner:
            if _key == key:
                return (value, unit)
        return default

    def __contains__(self, key):
        """Return `True` if `key` is present, else `False`.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> 'Fan speed' in statusdict
        True
        >>> 'Pump speed' in statusdict
        False
        >>> 'Pump speed' not in statusdict
        True
        """

        return key in self.keys()

    def __iter__(self):
        """Return an iterator over the keys of the map.

        This is a shortcut for `iter(d.keys())`.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> ", ".join(statusdict)
        'Temperature, Fan speed'
        """

        return self.keys()

    def keys(self, unit=None):
        """Return a new view of the map’s keys.

        If `unit` is supplied, only the keys for values with unit `unit` are
        returned.

        Since both the inner list and the `StatusDict` object are not allowed
        to mutate, this returns a simple iterator over the keys.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> ", ".join(statusdict.keys())
        'Temperature, Fan speed'
        >>> ", ".join(statusdict.keys('°C'))
        'Temperature'
        """

        if unit is None:
            return (key for key, _, _, in self.inner)
        else:
            return (key for key, _, _unit, in self.inner if _unit == unit)

    def items(self, unit=None):
        """Return a new view of the map’s items (`(key, value, unit)` tuples).

        If `unit` is supplied, only the items with unit `unit` are returned.

        Since both the inner list and the `StatusDict` object are not allowed
        to mutate, this returns a simple iterator over the items.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> list(statusdict.items())
        [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> list(statusdict.items('°C'))
        [('Temperature', 32.5, '°C')]
        """

        if unit is None:
            yield from self.inner
        else:
            for key, value, _unit in self.inner:
                if _unit == unit:
                    yield (key, value, _unit)

    def values(self, unit=None):
        """Return a new view of the map’s values (`(value, unit)` pairs).

        If `unit` is supplied, only the values with unit `unit` are returned.

        Since both the inner list and the `StatusDict` object are not allowed
        to mutate, this returns a simple iterator over the values.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> list(statusdict.values())
        [(32.5, '°C'), (1435, 'rpm')]
        >>> list(statusdict.values('°C'))
        [(32.5, '°C')]
        """

        if unit is None:
            return ((value, _unit) for _, value, _unit in self.inner)
        else:
            return ((value, _unit) for _, value, _unit in self.inner if _unit == unit)

    def copy(self):
        """Return a shallow copy of the map.

        The inner is shared between both original and copy `StatusDict`, and
        thus should not be mutated while still wrapped by either one of them.

        >>> status = [('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')]
        >>> statusdict = StatusDict(status)
        >>> copy = statusdict.copy()
        >>> copy == statusdict
        True
        >>> copy is statusdict
        False
        """

        return StatusDict(self.inner)

    def __eq__(self, other):
        """Compare if `self` and `other` are equal.

        Two `StatusDict` compare equal if they have the same `(key, value,
        unit)` tuples, regardless of ordering.

        >>> status = StatusDict([('Temperature', 32.5, '°C'), ('Fan speed', 1435, 'rpm')])
        >>> other = StatusDict([('Fan speed', 1435, 'rpm'), ('Temperature', 32.5, '°C')])
        >>> status == status
        True
        >>> status == other
        True
        >>> status == StatusDict([('Temperature', 32.5, '°C')])
        False
        """

        if len(self) != len(other):
            return False
        for key, value, unit in self.items():
            try:
                if (value, unit) != other[key]:
                    return False
            except KeyError:
                return False
        return True


if __name__ == "__main__":
    """Benchmark it."""

    from timeit import timeit

    # a sample of a comparably large output from get_status()
    status_list = [
        ("Fan 1", "PWM", ""),
        ("Fan 1 current", 0.03, "A"),
        ("Fan 1 speed", 1461, "rpm"),
        ("Fan 1 voltage", 11.91, "V"),
        ("Fan 2", "PWM", ""),
        ("Fan 2 current", 0.02, "A"),
        ("Fan 2 speed", 1336, "rpm"),
        ("Fan 2 voltage", 11.91, "V"),
        ("Fan 3", "PWM", ""),
        ("Fan 3 current", 0.04, "A"),
        ("Fan 3 speed", 1649, "rpm"),
        ("Fan 3 voltage", 11.91, "V"),
        ("Firmware version", "1.0.7", ""),
        ("LED accessories", 2, ""),
        ("LED accessory type", "HUE+ Strip", ""),
        ("LED count (total)", 20, ""),
        ("Noise level", 63, "dB"),
    ]

    # an equivalent python dictionary
    status_dict = {
        "Fan 1": ("PWM", ""),
        "Fan 1 current": (0.03, "A"),
        "Fan 1 speed": (1461, "rpm"),
        "Fan 1 voltage": (11.91, "V"),
        "Fan 2": ("PWM", ""),
        "Fan 2 current": (0.02, "A"),
        "Fan 2 speed": (1336, "rpm"),
        "Fan 2 voltage": (11.91, "V"),
        "Fan 3": ("PWM", ""),
        "Fan 3 current": (0.04, "A"),
        "Fan 3 speed": (1649, "rpm"),
        "Fan 3 voltage": (11.91, "V"),
        "Firmware version": ("1.0.7", ""),
        "LED accessories": (2, ""),
        "LED accessory type": ("HUE+ Strip", ""),
        "LED count (total)": (20, ""),
        "Noise level": (63, "dB"),
    }

    # an equivalent StatusDict
    status_wrapper = StatusDict(status_list)

    def print_time(func_name, func=None):
        if func is None:
            func = globals()[func_name]
        number = 1_000_000
        t = timeit(func, number=number)
        print(f"{func_name}: {t / number * 1e9:0.1f} ns/exec")
        return t

    # baseline and/or raw operations on basic Python types

    print_time("baseline", "42")

    def baseline_call():
        return 42

    print_time("baseline_call")
    print_time("baseline_lambda", lambda: 42)

    print_time("raw_getitem_list", lambda: status_list[10])

    print_time("construct_2tuple", lambda: (1649, "rpm"))
    print_time("construct_3tuple", lambda: ("Fan 3 speed", 1649, "rpm"))

    def destruct_2tuple():
        value, unit = (1649, "rpm")

    def destruct_3tuple():
        key, value, unit = ("Fan 3 speed", 1649, "rpm")

    print_time("destruct_2tuple")
    print_time("destruct_3tuple")

    print_time("raw_getitem_2tuple", lambda: (1649, "rpm")[0])
    print_time("raw_getitem_3tuple", lambda: ("Fan 3 speed", 1649, "rpm")[0])

    print_time("raw_len_list", lambda: len(status_list))
    print_time("len_wrapper", lambda: len(status_wrapper))  # cost of indirections

    # count: iterate the collection and count the number of items

    def count_list():
        cnt = 0
        for _ in status_list:
            cnt += 1
        return cnt

    def count_list_destructure():
        cnt = 0
        for _, _, _ in status_list:
            cnt += 1
        return cnt

    def count_list_functional():
        return sum(1 for _ in status_list)

    assert count_list() == 17
    assert count_list_destructure() == 17
    assert count_list_functional() == 17

    print_time("count_list")
    print_time("count_list_destructure")
    print_time("count_list_functional")

    def count_dict():
        cnt = 0
        for _ in status_dict:
            cnt += 1
        return cnt

    def count_dict_destructure():
        cnt = 0
        for _, (_, _) in status_dict.items():
            cnt += 1
        return cnt

    def count_dict_functional():
        return sum(1 for _ in status_dict)

    assert count_dict_destructure() == 17
    assert count_dict() == 17
    assert count_dict_functional() == 17

    print_time("count_dict_destructure")
    print_time("count_dict")
    print_time("count_dict_functional")

    def count_wrapper():
        cnt = 0
        for _ in status_wrapper.items():  # avoids conversion
            cnt += 1
        return cnt

    def count_wrapper_destructure():
        cnt = 0
        for _, _, _ in status_wrapper.items():
            cnt += 1
        return cnt

    def count_wrapper_functional():
        return sum(1 for _ in status_wrapper.items())  # avoids conversion

    assert count_wrapper() == 17
    assert count_wrapper_destructure() == 17
    assert count_wrapper_functional() == 17

    print_time("count_wrapper")
    print_time("count_wrapper_destructure")
    print_time("count_wrapper_functional")

    # getitem/get: get (value, unit) for key

    def getitem_manual_list():
        for key, value, unit in status_list:
            if key == "Fan 3 speed":
                return (value, unit)
        raise KeyError("Fan 3 speed")

    def getitem_dict():
        return status_dict["Fan 3 speed"]

    def getitem_wrapper():
        return status_wrapper["Fan 3 speed"]

    assert getitem_manual_list() == (1649, "rpm")
    assert getitem_dict() == (1649, "rpm")
    assert getitem_wrapper() == (1649, "rpm")

    print_time("getitem_manual_list")
    print_time("getitem_dict")
    print_time("getitem_wrapper")

    # iterate on a specific unit

    def sum_rpm_dict():
        return sum(value for value, unit in status_dict.values() if unit == "rpm")

    def sum_rpm_wrapper():
        return sum(value for value, _ in status_wrapper.values("rpm"))

    def sum_rpm_wrapper_external_if():
        return sum(value for value, unit in status_wrapper.values() if unit == "rpm")

    def sum_rpm_wrapper_use_items():
        return sum(value for _, value, _ in status_wrapper.items("rpm"))

    assert sum_rpm_dict() == 4446
    assert sum_rpm_wrapper() == 4446
    assert sum_rpm_wrapper_external_if() == 4446
    assert sum_rpm_wrapper_use_items() == 4446

    print_time("sum_rpm_dict")
    print_time("sum_rpm_wrapper")
    print_time("sum_rpm_wrapper_external_if")
    print_time("sum_rpm_wrapper_use_items")


#     print(
#         "Search with Python dictionary",
#         timeit("status_dict['Fan 3 speed']", setup=setup)
#     )

#     assert status_wrapper['Fan 3 speed'] == (1649, 'rpm')
#     print(
#         "Search with StatusDict wrapper",
#         timeit("status_wrapper['Fan 3 speed']", setup=setup)
#     )

#     assert sum(1 for _, unit in status_dict.values() if unit == 'V') == 3
#     print(
#         "Count all voltages with Python dictionary",
#         timeit("sum(1 for _, unit in status_dict.values() if unit == 'V')", setup=setup)
#     )

#     assert sum(1 for _ in status_wrapper.items('V')) == 3
#     print(
#         "Count all voltages with StatusDict wrapper",
#         timeit("sum(1 for _ in status_wrapper.items('V'))", setup=setup)
#     )

#     assert count_all(status_list) == 17
#     print(
#         "Count all (iterate) items with list",
#         timeit('count_all(status_list)', setup=setup)
#     )

#     assert count_all(status_dict) == 17
#     print(
#         "Count all (iterate) items with Python dictionary",
#         timeit('count_all(status_dict)', setup=setup)
#     )

#     assert count_all(status_wrapper) == 17
#     print(
#         "Count all (iterate) items with StatusDict wrapper",
#         timeit('count_all(status_wrapper)', setup=setup)
#     )
