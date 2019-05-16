NET=traffic
INPUT_IMAGE=test046.png
MAIN=main.cpp

INPUT_FILES=$(INPUT_IMAGE)

#Caffe frontend flags
FRONTEND_FLAGS=
#FRONTEND_FLAGS+= --log-level=INFO

# Design Space Exploration flags
DSE_FLAGS=
#DSE_FLAGS+= --log-level=INFO
#DSE_FLAGS+= --dse-no-tiling   #no tiling to speed up DSE
#DSE_FLAGS+= --exp-ignore-output-buffers #ignore output buffers which can not be validated by halide experiments
#DSE_FLAGS+= --dse-all

# Halide Code Generation flags
BACKEND_FLAGS=
#BACKEND_FLAGS+=--halide-trace-code
#BACKEND_FLAGS+=--halide-debug-code
#BACKEND_FLAGS+=--halide-profile-code


#######################################################
#
# Custom targets for this network
#

all:$(addsuffix _check,$(NET))

%_check:%_output.txt reference.txt
	@cmp $^ && (touch $@; echo "Output matches reference!") || echo "Output does NOT match reference!!"

#declare what we generate so it will be precious and cleaned
TGT_SUFFIXES=_output.txt _check
include ../Makefile
