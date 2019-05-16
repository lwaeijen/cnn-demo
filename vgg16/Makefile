#######################################################
#
# Network Config
#
NET=vgg16
INPUT_IMAGE=koala.jpeg
SCALED_IMAGE=scaled_$(INPUT_IMAGE)
LABELS=labels.txt
INPUT_FILES=$(SCALED_IMAGE) $(LABELS)
MAIN=main.cpp


#######################################################
#
# Possibly override default flags from main Makefile
#
FRONTEND_FLAGS=
DSE_FLAGS=
BACKEND_FLAGS=


#######################################################
#
# Execute and Verify targets for this network
#

all:$(NET)_check ## Generate random schedule, implement, compile and execute the network, and finally verify the results

%_check:%_output.txt
	@grep -i "koala" $< && (touch $@; echo "Correctly identified a Koala!") || echo "Error: image NOT classified as a koala"


#######################################################
#
# Download targets to save repo space
#

$(NET).prototxt:
	wget https://gist.githubusercontent.com/ksimonyan/211839e770f7b538e2d8/raw/0067c9b32f60362c74f4c445a080beed06b07eb3/VGG_ILSVRC_16_layers_deploy.prototxt -O $@

$(NET).caffemodel:
	wget http://www.robots.ox.ac.uk/~vgg/software/very_deep/caffe/VGG_ILSVRC_16_layers.caffemodel -O $@

$(INPUT_IMAGE):
	wget http://farm1.static.flickr.com/159/403176078_a2415ddf33.jpg  -O $@

$(SCALED_IMAGE):$(INPUT_IMAGE)
	convert $< -resize 224x224! $@

$(LABELS):
	wget https://raw.githubusercontent.com/HoldenCaulfieldRye/caffe/master/data/ilsvrc12/synset_words.txt -O $@
	sed -i 's/^n[0-9]\+\s*//' $@


#######################################################
#
# Include root makefile and pass generated targets for clean
#
TGT_SUFFIXES=_check .prototxt .caffemodel
GENERATED=$(INPUT_IMAGE) $(SCALED_IMAGE) $(LABELS)
include ../Makefile
