NET=vdsr
IMAGE_NAME=baby
HIGHRES_IMAGE=$(IMAGE_NAME)_highres.bmp
HIGHRES_CROP_IMAGE=$(IMAGE_NAME)_highres_crop.jpeg
LOWRES_SMALL_IMAGE=$(IMAGE_NAME)_lowres_small.jpeg
LOWRES_LARGE_IMAGE=$(IMAGE_NAME)_lowres_large.jpeg
OUTPUT_IMAGE=$(IMAGE_NAME)_restored.jpeg
MAIN=main.cpp

# Caffe frontend flags
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

INPUT_FILES=  $(LOWRES_LARGE_IMAGE)
OUTPUT_FILES= $(OUTPUT_IMAGE)

#######################################################
#
# Custom targets for this network
#
all:$(addsuffix _output.txt,$(NET))


#######################################################
#
# Download targets to save repo space
#

vdsr.prototxt:
	wget https://github.com/huangzehao/caffe-vdsr/raw/master/Train/VDSR_net_deploy.prototxt -O $@

vdsr.caffemodel:
	wget https://github.com/huangzehao/caffe-vdsr/raw/master/Train/VDSR_Adam.caffemodel -O $@

$(HIGHRES_IMAGE):
	wget https://github.com/huangzehao/caffe-vdsr/raw/master/Test/Data/Set5/baby_GT.bmp -O $@

#resize to network size. Also transform to jpeg which is supported by the halide load_image commands
$(HIGHRES_CROP_IMAGE):$(HIGHRES_IMAGE)
	convert $< -adaptive-resize 256x256! $@

#downscale with a factor of 3
$(LOWRES_SMALL_IMAGE):$(HIGHRES_CROP_IMAGE)
	convert $< -adaptive-resize 85x85! $@

#upsample again with a factor of 3 (data loss has happened in between)
$(LOWRES_LARGE_IMAGE):$(LOWRES_SMALL_IMAGE)
	convert $< -interpolative-resize 256x256! $@

#declare what we generate so it will be precious and cleaned
TGT_SUFFIXES=.prototxt .caffemodel
GENERATED=$(HIGHRES_IMAGE) $(HIGHRES_CROP_IMAGE) $(LOWRES_SMALL_IMAGE) $(LOWRES_LARGE_IMAGE) $(OUTPUT_IMAGE)
include ../Makefile
