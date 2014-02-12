#!/usr/bin/make -f

# enable or disable tests here:
TESTS := test1 test2 test3 test4

all: scripts $(TESTS)

test%:
	make -C t$* run
	make -C t$* check

clean-test%:
	make -C t$* clean

scripts:
	sh ./test_scripts.sh

clean: $(TESTS:%=clean-%)
	rm -f *\.dsc *\.tar\.gz *\.build *\.changes *\.deb
	@find . -prune -name '*.egg-info' -exec rm -rf '{}' ';' || true

.PHONY: clean
