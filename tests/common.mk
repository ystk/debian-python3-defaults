#!/usr/bin/make -f

export DEBPYTHON3_DEFAULT ?= $(shell sed -rne 's,^default-version = python(.*),\1,p' ../../debian/debian_defaults)
export DEBPYTHON3_SUPPORTED ?= $(shell sed -rne '/^supported-versions/{s/^supported-versions = (.*)/\1/g;s/python//g}' ../../debian/debian_defaults)

all: run check

run: clean
	dpkg-buildpackage -b -us -uc

clean-common:
	./debian/rules clean
