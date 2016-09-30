#!/usr/bin/env bash
#   Version: 2014.105
EXEC='kx_app_name'
MOD='pn4'

LD_LIBRARY_PATH=${KX}/lib

h=$@

if [ ! -z "${KX}" ]
then
	PYTHON=pnpython4
	export PYTHON
        PYTHONPATH=${KX}/apps/${MOD}
        export PYTHONPATH
else
        echo "KX environment not set! Can not continue."
	exit
fi

if [ -z "$PYTHON" ]
then
	echo "$PYTHON not found!"
	exit
fi

${PYTHON} ${KX}/apps/${MOD}/${EXEC}.py $h
