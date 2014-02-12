#!/usr/bin/make -f

all: run check

DPY=$(shell ../../debian/py3versions -vd)  # Python >= 3.2

run: clean
	dpkg-buildpackage -b -us -uc

check:
	grep -q "py3compile -p python3-foo /usr/lib/python3-foo"\
		debian/python3-foo/DEBIAN/postinst
	test -f debian/python3-foo/usr/lib/python3/dist-packages/foo/bar.cpython-*mu.so

clean:
	./debian/rules clean
	rm -rf lib/Foo.egg-info build
