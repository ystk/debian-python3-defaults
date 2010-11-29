#!/usr/bin/make -f

all: scripts test1

test%:
	(cd t$*; debuild -us -uc)

scripts:
	sh ./test_scripts.sh

clean:
	rm -f *\.dsc *\.tar\.gz *\.build *\.changes *\.deb
	(cd t1; ./debian/rules clean)
	@find . -name '*\.egg-info' -exec rm -rf "{}" \; || true

.PHONY: clean
