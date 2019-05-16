#######################################################
#
# Network Config
#
NET=vgg19
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
	wget http://gist.githubusercontent.com/ksimonyan/3785162f95cd2d5fee77/raw/f02f8769e64494bcd3d7e97d5d747ac275825721/VGG_ILSVRC_19_layers_deploy.prototxt -O $@

$(NET).caffemodel:
	wget http://www.robots.ox.ac.uk/~vgg/software/very_deep/caffe/VGG_ILSVRC_19_layers.caffemodel -O $@

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
