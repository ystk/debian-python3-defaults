# -*- coding: UTF-8 -*-
# Copyright © 2010 Piotr Ożarowski <piotr@debian.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import re
from os.path import exists
from types import GeneratorType

SUPPORTED = [(3, 1)]
DEFAULT = (3, 1)
RANGE_PATTERN = r'(-)?(\d\.\d+)(?:(-)(\d\.\d+)?)?'
RANGE_RE = re.compile(RANGE_PATTERN)


def get_requested_versions(vrange=None, available=None):
    """Return a set of requested and supported Python versions.

    :param available: if set to `True`, return installed versions only,
        if set to `False`, return requested versions that are not installed.
        By default returns all requested versions.
    :type available: bool

    >>> sorted(get_requested_versions([(3, 0), None]))
    [(3, 1)]
    >>> sorted(get_requested_versions('')) == sorted(SUPPORTED)
    True
    >>> sorted(get_requested_versions([None, None])) == sorted(SUPPORTED)
    True
    >>> get_requested_versions([(5, 0), None])
    set()
    """
    if isinstance(vrange, str):
        vrange = parse_vrange(vrange)

    if not vrange or list(vrange) == [None, None]:
        versions = set(SUPPORTED)
    else:
        minv = (0, 0) if vrange[0] is None else vrange[0]
        maxv = (99, 99) if vrange[1] is None else vrange[1]
        if minv == maxv:
            versions = set((minv,) if minv in SUPPORTED else tuple())
        else:
            versions = set(v for v in SUPPORTED if minv <= v < maxv)

    if available:
        versions = set(v for v in versions \
                       if exists("/usr/bin/python%d.%d" % v))
    elif available is False:
        versions = set(v for v in versions \
                       if not exists("/usr/bin/python%d.%d" % v))

    return versions


def parse_vrange(value):
    """Return minimum and maximum Python version from given range.

    >>> parse_vrange('3.0-')
    ((3, 0), None)
    >>> parse_vrange('3.1-3.3')
    ((3, 1), (3, 3))
    >>> parse_vrange('3.2-4.0')
    ((3, 2), (4, 0))
    >>> parse_vrange('-3.7')
    (None, (3, 7))
    >>> parse_vrange('3.2')
    ((3, 2), (3, 2))
    >>> parse_vrange('') == parse_vrange('-') == (None, None)
    True
    """
    if value in ('', '-'):
        return None, None

    match = RANGE_RE.match(value)
    if not match:
        raise ValueError("version range is invalid: %s" % value)
    groups = match.groups()

    if list(groups).count(None) == 3:  # only one version is allowed
        minv = tuple(int(i) for i in groups[1].split('.'))
        return minv, minv

    minv = maxv = None
    if groups[0]:  # maximum version only
        maxv = groups[1]
    else:
        minv = groups[1]
        maxv = groups[3]

    minv = tuple(int(i) for i in minv.split('.')) if minv else None
    maxv = tuple(int(i) for i in maxv.split('.')) if maxv else None

    if maxv and minv and minv > maxv:
        raise ValueError("version range is invalid: %s" % value)

    return minv, maxv


def parse_pycentral_vrange(value):
    """Parse XS-Python-Version.

    >>> parse_pycentral_vrange('>= 3.1')
    ((3, 1), None)
    >>> parse_pycentral_vrange('<< 4.0')
    (None, (4, 0))
    >>> parse_pycentral_vrange('3.1')
    ((3, 1), (3, 1))
    >>> parse_pycentral_vrange('3.1, 3.2')
    ((3, 1), None)
    """
    get = lambda x: get_requested_versions(parse_vrange(x))

    minv = maxv = None
    hardcoded = set()

    for item in value.split(','):
        item = item.strip()

        match = re.match('>=\s*([\d\.]+)', item)
        if match:
            minv = "%.3s" % match.group(1)
            continue
        match = re.match('<<\s*([\d\.]+)', item)
        if match:
            maxv = "%.3s" % match.group(1)
            continue
        match = re.match('^[\d\.]+$', item)
        if match:
            hardcoded.add("%.3s" % match.group(0))

    if len(hardcoded) == 1:
        ver = hardcoded.pop()
        return getver(ver), getver(ver)

    if not minv and hardcoded:
        # yeah, no maxv!
        minv = sorted(hardcoded)[0]

    return getver(minv) if minv else None, \
           getver(maxv) if maxv else None


def vrange_str(vrange):
    """Return version range string from given range.

    >>> vrange_str(((3, 4), None))
    '3.4-'
    >>> vrange_str(((3, 4), (3, 6)))
    '3.4-3.6'
    >>> vrange_str(((3, 4), (4, 0)))
    '3.4-4.0'
    >>> vrange_str((None, (3, 7)))
    '-3.7'
    >>> vrange_str(((3, 5), (3, 5)))
    '3.5'
    >>> vrange_str((None, None))
    '-'
    """
    if vrange[0] is vrange[1] is None:
        return '-'
    if vrange[0] == vrange[1]:
        return '.'.join(str(i) for i in vrange[0])
    elif vrange[0] is None:
        return '-' + '.'.join(str(i) for i in vrange[1])
    elif vrange[1] is None:
        return '.'.join(str(i) for i in vrange[0]) + '-'
    else:
        return "%s-%s" % ('.'.join(str(i) for i in vrange[0]),
                          '.'.join(str(i) for i in vrange[1]))


def vrepr(value):
    """
    >>> vrepr(([3, 4], [3, 2]))
    ['3.4', '3.2']
    >>> vrepr(('2.6', '3.1'))
    ['2.6', '3.1']
    >>> vrepr('3.2')
    '3.2'
    >>> vrepr((3, 2))
    '3.2'
    """
    if isinstance(value, str):
        return value
    elif not isinstance(value, (GeneratorType, set))\
      and isinstance(value[0], int):
        return '.'.join(str(i) for i in value)

    result = []
    for version in value:
        if isinstance(version, str):
            result.append(version)
        else:
            result.append('.'.join(str(i) for i in version))
    return result


def getver(value):
    """Return pair of integers that represent version.

    >>> getver('3.2')
    (3, 2)
    >>> getver('3.1.4')
    (3, 1)
    >>> getver(None)
    ''
    """
    if not value:
        return ''
    return tuple(int(i) for i in value.split('.', 2))[:2]


def debsorted(versions, return_str=None):
    """Return sorted list of versions starting with default Python
    version (if available) then list of suppored versions greater than default
    one followed by reversed list of older versions.

    List of versions sorted this way can be used in Depends field.

    :param vrepr: return string represenatations of versions, by default the
        same format is used as in :param:`versions`

    >>> debsorted([(2, 6), (3, 1), (2, 5), (2, 4), (2, 7)])[0] == DEFAULT
    True
    >>> debsorted(('2.4', '3.2', '2.6', '2.7'))[-1]
    (2, 4)
    >>> debsorted(set([(2, 1), (2, 2)]))
    [(2, 2), (2, 1)]
    >>> debsorted([(2, 1), (2, 2)], return_str=True)
    ['2.2', '2.1']
    """
    result = []
    old_versions = []
    for version in sorted(versions):
        if isinstance(version, str):
            version = getver(version)
        if version < DEFAULT:
            old_versions.append(version)
        else:
            result.append(version)
    result.extend(reversed(old_versions))
    if return_str and result:
        return vrepr(result)
    return result
