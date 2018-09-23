"""Utilities for profile manipulation.

Copyright (C) 2018  Jonas Malaco
Copyright (C) 2018  each contribution's author

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import itertools
import sys


def delta(profile):
    """Compute a profile's Δx and Δy."""
    return [(cur[0]-prev[0], cur[1]-prev[1])
            for cur,prev in zip(profile[1:], profile[:-1])]


def normalize_profile(profile, critx):
    """Normalize a [(x:int, y:int), ...] profile.

    The normalized profile will ensure that:

     - the profile is a monotonically increasing function
       (i.e. for every i, i > 1, x[i] - x[i-1] > 0 and y[i] - y[i-1] >= 0)
     - the profile is sorted
     - a (critx, 100) failsafe is enforced

    >>> normalize_profile([(30, 40), (25, 25), (35, 30), (40, 35), (40, 80)], 60)
    [(25, 25), (30, 40), (35, 40), (40, 80), (60, 100)]
    """
    profile = sorted(list(profile) + [(critx, 100)], key=lambda p: (p[0], -p[1]))
    mono = profile[0:1]
    for (x, y), (xb, yb) in zip(profile[1:], profile[:-1]):
        if x == xb:
            continue
        if y < yb:
            y = yb
        mono.append((x, y))
    return mono


def autofill_profile(profile, n):
    """Autofill a [(x: int, y: int), ...] profile up to n points.

    Requires the profile to be sorted by x, with no duplicate x values (see
    normalize_profile).  Simultaneously expects and returns profiles with
    integer x and y values.

    The resulting profile is optimized for systems that do not interpolate
    between points.  For these systems it is advantageous to reduce the larger
    Δy increments, thus reducing the errors between the system output and
    theorically interpolated intermediate points.

    All points present in the input are kept.  The output might have fewer than
    n – down to len(profile) – points, if the profile is either too flat or too
    complex.

    >>> autofill_profile([(25, 25), (30, 40), (40, 80), (60, 100)], 7)
    [(25, 25), (30, 40), (33, 53), (37, 67), (40, 80), (50, 90), (60, 100)]
    >>> autofill_profile([(25, 25), (30, 25), (60, 100)], 7)
    [(25, 25), (30, 25), (36, 40), (42, 55), (48, 70), (54, 85), (60, 100)]
    >>> autofill_profile([(25, 100), (60, 100)], 7)
    [(25, 100), (60, 100)]
    >>> autofill_profile([(25, 100)], 7)
    [(25, 100)]
    """
    deltas = delta(profile)
    totaldy = sum(dy for _,dy in deltas)
    if totaldy == 0:
        return profile
    # discount from n any steps that only keep points from the input
    n -= sum(1 for dx,dy in deltas if round((n - 1)*dy/totaldy) == 0)
    # all points present in the input are kept; do not overshoot dx
    steps = iter(max(1, min(round((n - 1)*dy/totaldy), dx))
                for dx,dy in deltas)
    tmp = iter([(round(x+dx*i/m), round(y+dy*i/m)) for i in range(0, m)]
               for (x,y),(dx,dy),m in zip(profile, deltas, steps))
    return list(itertools.chain(*tmp)) + profile[-1:]


def interpolate_profile(profile, x):
    """Interpolate y given x and a [(x: int, y: int), ...] profile.

    Requires the profile to be sorted by x, with no duplicate x values (see
    normalize_profile).  Expects profiles with integer x and y values, and
    returns duty rounded to the nearest integer.

    >>> interpolate_profile([(20, 50), (50, 70), (60, 100)], 33)
    59
    >>> interpolate_profile([(20, 50), (50, 70)], 19)
    50
    >>> interpolate_profile([(20, 50), (50, 70)], 51)
    70
    >>> interpolate_profile([(20, 50)], 20)
    50
    """
    lower, upper = profile[0], profile[-1]
    for step in profile:
        if step[0] <= x:
            lower = step
        if step[0] >= x:
            upper = step
            break
    if lower[0] == upper[0]:
        return lower[1]
    return round(lower[1] + (x - lower[0])/(upper[0] - lower[0])*(upper[1] - lower[1]))
