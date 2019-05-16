#######################################################
#
# Network Config
#
NET=resnet101
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
	wget "https://onedrive.live.com/download.aspx?cid=4006CBB8476FF777&authKey=%21AAFW2%2DFVoxeVRck&resid=4006CBB8476FF777%2117892&ithint=%2Eprototxt" -O $@

$(NET).caffemodel:
	wget "https://onedrive.live.com/download.aspx?cid=4006CBB8476FF777&authKey=%21AAFW2%2DFVoxeVRck&resid=4006CBB8476FF777%2117896&ithint=%2Ecaffemodel" -O $@

$(INPUT_IMAGE):
	wget "http://farm1.static.flickr.com/159/403176078_a2415ddf33.jpg" -O $@

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
