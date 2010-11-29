#! /bin/sh

set -e

# clean previous results
find t1/lib -name *.pyc -delete
find t1/lib -type d -name __pycache__ | xargs rm -rf

# create 3.1's pyc files only
if [ -x /usr/bin/python3.1 ]; then
	../py3compile t1/lib/ -vV 3.1
	test -f t1/lib/foo/__init__.pyc -a \! -d t1/lib/foo/__pycache__ \
		|| (echo "E: Byte-compiling for python3.1 failed"; false)
fi

# create __pycache__/*.pyc files only
if [ -x /usr/bin/python3.2 ]; then
	../py3compile t1/lib/ -vV 3.2
	test -f t1/lib/foo/__pycache__/__init__.cpython-32.pyc \
		|| (echo "E: Byte-compiling for python3.2 failed"; false)
fi

# remove 3.1's pyc files only
if [ -x /usr/bin/python3.1 ]; then
	../py3clean t1/lib/ -vV 3.1
	# python3.1 files should be gone
	test -f t1/lib/foo/__init__.pyc \
		&& (echo "E: removing python3.1's pyc files failed"; false)
fi

if [ -x /usr/bin/python3.2 ]; then
	# check if python3.2 files are still there
	test ! -f t1/lib/foo/__pycache__/__init__.cpython-32.pyc \
	     && (echo "E: removing python3.1's pyc files (and not touching python3.2's ones) failed"; false)

	# remove __pycache__/*.pyc files
	../py3clean t1/lib/ -vV 3.2
	[ `find t1/lib/foo/ -type d -name __pycache__ | wc -l` = "0" ] \
	|| echo "E: removing python3.2's pyc files failed"
fi

exit 0
