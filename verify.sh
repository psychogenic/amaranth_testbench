#!/bin/bash

NAME=$1
OPTIONS=$2
DEFAULTOPTIONS="--cover "
SBYOPTIONS=$3

PYTHONBIN=python
TESTSDIR=tests
EXAMPLESDIR=amaranth_testbench/examples

if [ "x$NAME" = "x" ]
then
	echo "USAGE $0 MODULE [BUILDOPTIONS [SBYOPTIONS]]"
	echo "  e.g. $0 counter_basic"
	echo "       $0 counter_basic --depthprobe"
	echo "       $0 counter_basic --depthprobe  cover"
	exit 1
fi

if [ "x$OPTIONS" = "x" ]
then
	OPTIONS=$DEFAULTOPTIONS
fi


MODULEPY=$EXAMPLESDIR/test_${NAME}.py
if [ -e $MODULEPY ]
then
	echo "Running $MODULEPY"
else
	echo "Can't find $MODULEPY"
	exit 2
fi

OUTILFILE=$TESTSDIR/${NAME}.il
SBYCONFIG=$TESTSDIR/${NAME}.sby
if [ -e $SBYCONFIG ]
then
	echo "Will use $SBYCONFIG $SBYOPTIONS"
else
	echo "Can't find $SBYCONFIG"
	exit 3
fi


$PYTHONBIN $MODULEPY verify $OPTIONS -t il > $OUTILFILE
sby -f $SBYCONFIG $SBYOPTIONS
