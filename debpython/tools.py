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
from os.path import isdir, islink, join, split
from debpython.version import getver

log = logging.getLogger(__name__)
EGGnPTH_RE = re.compile(r'(.*?)(-py\d\.\d(?:-[^.]*)?)?(\.egg-info|\.pth)$')
SHEBANG_RE = re.compile(r'^#!\s*/usr/bin/(?:env\s+)?(python(\d+(?:\.\d+)?)?(?:-dbg)?).*')


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


def shebang2pyver(fname):
    """Check file's shebang.

    :rtype: tuple
    :returns: pair of Python interpreter string and Python version
    """
    try:
        with open(fname) as fp:
            data = fp.read(32)
            match = SHEBANG_RE.match(data)
            if not match:
                return None
            res = match.groups()
            if res != (None, None):
                if res[1]:
                    if len(res[1]) == 1:  # "python3"
                        res = (res[0], None)
                    else:
                        res = res[0], getver(res[1])
                return res
    except IOError:
        log.error('cannot open %s', fname)


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
