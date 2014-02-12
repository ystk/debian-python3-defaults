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

import logging
import os
import re
from pickle import dumps
from os.path import exists, isdir, islink, join, split
from subprocess import PIPE, Popen
from debpython.version import SUPPORTED, getver, vrepr

log = logging.getLogger(__name__)
EGGnPTH_RE = re.compile(r'(.*?)(-py\d\.\d(?:-[^.]*)?)?(\.egg-info|\.pth)$')
SHEBANG_RE = re.compile(r'^#!\s*(.*?/bin/.*?)(python(?:(3.\d+)|3)(?:-dbg)?)(?:\s(.*))?')



def sitedir(version, package=None, gdb=False):
    """Return path to site-packages directory.

    Note that returned path is not the final location of .py files

    >>> sitedir((3, 1))
    '/usr/lib/python3/dist-packages/'
    >>> sitedir((3, 1), 'python-foo', True)
    'debian/python-foo/usr/lib/debug/usr/lib/python3/dist-packages/'
    >>> sitedir((3, 2))
    '/usr/lib/python3/dist-packages/'
    """
    if isinstance(version, str):
        version = tuple(int(i) for i in version.split('.'))

    path = '/usr/lib/python3/dist-packages/'

    if gdb:
        path = "/usr/lib/debug%s" % path
    if package:
        path = "debian/%s%s" % (package, path)

    return path


def relpath(target, link):
    """Return relative path.

    >>> relpath('/usr/share/python-foo/foo.py', '/usr/bin/foo', )
    '../share/python-foo/foo.py'
    """
    t = target.split('/')
    l = link.split('/')
    while l[0] == t[0]:
        del l[0], t[0]
    return '/'.join(['..'] * (len(l) - 1) + t)


def relative_symlink(target, link):
    """Create relative symlink."""
    return os.symlink(relpath(target, link), link)


def move_file(fpath, dstdir):
    """Move file to dstdir. Works with symlinks (including relative ones)."""
    if isdir(fpath):
        dname = split(fpath)[-1]
        for fn in os.listdir(fpath):
            move_file(join(fpath, fn), join(dstdir, dname))

    if islink(fpath):
        dstpath = join(dstdir, split(fpath)[-1])
        relative_symlink(os.readlink(fpath), dstpath)
        os.remove(fpath)
    else:
        os.rename(fpath, dstdir)


def fix_shebang(fpath, replacement=None):
    """Normalize file's shebang.

    :param replacement: new shebang command (path to interpreter and options)
    """
    try:
        with open(fpath, 'rb') as fp:
            fcontent = fp.readlines()
            if not fcontent:
                log.info('fix_shebang: ignoring empty file: %s', fpath)
                return None
            try:
                first_line = str(fcontent[0], 'utf8')
            except UnicodeDecodeError:
                return None
    except IOError:
        log.error('cannot open %s', fpath)
        return False

    match = SHEBANG_RE.match(first_line)
    if not match:
        return None
    if not replacement:
        path, interpreter, version, argv = match.groups()
        if path != '/usr/bin':  # f.e. /usr/local/* or */bin/env
            replacement = "/usr/bin/%s" % interpreter
        if replacement and argv:
            replacement += " %s" % argv
    if replacement:
        log.info('replacing shebang in %s (%s)', fpath, first_line)
        # do not catch IOError here, the file is zeroed at this stage so it's
        # better to fail dh_python2
        with open(fpath, 'wb') as fp:
            fp.write(("#! %s\n" % replacement).encode('utf-8'))
            fp.writelines(fcontent[1:])
    return True


def shebang2pyver(fpath):
    """Check file's shebang.

    :rtype: tuple
    :returns: pair of Python interpreter string and Python version
    """
    try:
        with open(fpath, 'rb') as fp:
            data = fp.read(64)
            if b"\0" in data:
                # binary file
                return None
            match = SHEBANG_RE.match(str(data, 'utf-8'))
            if not match:
                return None
            res = match.groups()
            if res[1:3] != (None, None):
                if res[2]:
                    return res[1], getver(res[2])
                return res[1], None
    except IOError:
        log.error('cannot open %s', fpath)


def clean_egg_name(name):
    """Remove Python version and platform name from Egg files/dirs.

    >>> clean_egg_name('python_pipeline-0.1.3_py3k-py3.1.egg-info')
    'python_pipeline-0.1.3_py3k.egg-info'
    >>> clean_egg_name('Foo-1.2-py2.7-linux-x86_64.egg-info')
    'Foo-1.2.egg-info'
    """
    match = EGGnPTH_RE.match(name)
    if match and match.group(2) is not None:
        return ''.join(match.group(1, 3))
    return name


class memoize:
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args, **kwargs):
        key = dumps((args, kwargs))
        if key not in self.cache:
            self.cache[key] = self.func(*args, **kwargs)
        return self.cache[key]


@memoize
def get_magic_tags_map(versions=None):
    """Return Python magic tags for installed Python versions.

    :param versions: list of versions to check
    """

    if not versions:
        versions = set(SUPPORTED)
    versions = set(versions) - {(3, 1)}
    cmd = ''
    for v in vrepr(versions):
        if not exists("/usr/bin/python%s" % v):
            log.debug("version %s not installed, skipping", v)
            continue

        cmd += "/usr/bin/python%s -c 'import imp; print(\"%s_\"" % (v, v) + \
               "+imp.get_tag())' && "

    result = {(3, 1): None}
    if not cmd:
        return result
    cmd = cmd[:-3]  # cut last '&& '
    log.debug("invoking %s", cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    if p.wait() != 0:
        log.debug(p.stderr.read())
        raise Exception('cannot get magic tags')
    else:
        for line in p.stdout:
            vers, magic_tag = str(line, 'utf-8').split('_', 2)
            # Python 3.X returns bytes
            magic_tag = magic_tag.strip().lstrip("b'").rstrip("'")
            result[getver(vers)] = magic_tag
    log.debug('magic tags map: %s', result)
    return result


@memoize
def get_magic_numbers_map(versions=None):
    """Return Python magic numbers for installed Python versions.

    :param versions: list of versions to check
    """

    if not versions:
        versions = set(SUPPORTED)
    versions = set(versions) - {(3, 1)}
    cmd = ''
    for v in vrepr(versions):
        if not exists("/usr/bin/python%s" % v):
            log.debug("version %s not installed, skipping", v)
            continue

        cmd += "/usr/bin/python%s -c 'import imp; print(\"%s_%%s\"" % (v, v) + \
               "% imp.get_magic())' && "

    result = {(3, 1): None}
    if not cmd:
        return result
    cmd = cmd[:-3]  # cut last '&& '
    log.debug("invoking %s", cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    if p.wait() != 0:
        log.debug(p.stderr.read())
        raise Exception('cannot get magic numbers')
    else:
        for line in p.stdout:
            vers, magic = str(line, 'utf-8').split('_', 2)
            # Python 3.X returns bytes
            result[getver(vers)] = eval(magic)
    log.debug('magic numbers map: %s', result)
    return result


def cache_from_source(fpath, version, debug_override=None):
    """Emulate Python 3.2's imp.cache_from_source.

    :param fpath: path to file name
    :param version: Python version
    :type version: tuple
    :param debug_override: if not ``None``, overrides ``__debug__``

    >>> cache_from_source('foo.py', (3, 1))
    'foo.pyc'
    >>> cache_from_source('bar/foo.py', (3, 2), False)
    'bar/__pycache__/foo.cpython-32.pyo'
    """
    if debug_override is None:
        debug_override = __debug__

    last_char = 'c' if debug_override else 'o'
    if version == (3, 1):
        return fpath + last_char

    tag_map = get_magic_tags_map()
    fdir, fname = split(fpath)
    return join(fdir, '__pycache__', "%s.%s.py%s" % \
                (fname[:-3], tag_map[version], last_char))
