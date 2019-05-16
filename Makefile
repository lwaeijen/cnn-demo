# Sets up a virtual python environment
VENV=.venv
ACT=./activate

ACTIVATE_SCRIPT=$(VENV)/bin/activate
INSTALL_DONE=$(VENV)/.install_done
VENV_PACKAGES=.pythonpackages


#######################################################
#
# Generic help target. All targets followed by double # will be printed
#
help: ## Show this help.
	@grep -h '##' $(MAKEFILE_LIST) | grep -v '###' | grep -v grep | sed -e 's/\\$$//' | sed -e 's/:.*##/: /'

#######################################################
#
# targets for installation of the virtual environment
#
.PHONY:install
install:$(INSTALL_DONE) ## Install python virtual environment with all required packages
$(INSTALL_DONE):$(ACT) $(VENV_PACKAGES)
	# In particular on our bare bone CI test runners the setuptools can be outdated without forcing an update
	bash -c "source $(ACT) && pip install -U pip wheel setuptools && pip install -r $(VENV_PACKAGES) && touch $@"
	ln -s $(BINDIR)/compare.sh $(VENV)/bin/compare

$(ACT):$(ACTIVATE_SCRIPT)
	ln -fs $< $@

$(ACTIVATE_SCRIPT):
	bash -c "export LC_ALL=C && virtualenv -p python2 $(VENV) || ( rm -rf $(VENV); exit 1 )"


#######################################################
#
# Some localization for generic network targets
#
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
BINDIR := $(ROOT)/utils

#######################################################
#
# Generic network targets
#

# Caffe frontend flags
ifeq ($(FRONTEND_FLAGS),)
FRONTEND_FLAGS+= --log-level=INFO
endif

# Default Design Space Exploration flags
ifeq ($(DSE_FLAGS),)
DSE_FLAGS+= --log-level=INFO
DSE_FLAGS+= --dse-no-tiling   #no tiling to speed up DSE
DSE_FLAGS+= --exp-ignore-output-buffers #ignore output buffers which can not be validated by halide experiments
#DSE_FLAGS+= --dse-all
endif

# Default optimization flags
ifeq ($(OPT_FLAGS),)
OPT_FLAGS+= --log-level=INFO
OPT_FLAGS+= --exp-ignore-output-buffers #ignore output buffers which can not be validated by halide experiments
endif

# Default Halide Code Generation flags
ifeq ($(BACKEND_FLAGS),)
#BACKEND_FLAGS+=--halide-trace-code
#BACKEND_FLAGS+=--halide-debug-code
#BACKEND_FLAGS+=--halide-profile-code
endif

# Path to current makefile for use after include
MAKE_PATH := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Helper function to wrap commands in bash shell with source virtual env
define act
    bash -c "source $(abspath $(MAKE_PATH)$(ACT)) && $(strip $(1))"
endef

# Execute network and store output in log file
%_output.txt:%.exe $(INPUT_FILES)
	./$< $(INPUT_FILES) $(OUTPUT_FILES) | tee  $@

# Compiled network executable
%.exe:%.cpp $(MAIN)
	g++ $< $(MAIN) -lHalide -lpthread -ldl -lz -lpng -ljpeg $(shell llvm-config --system-libs 2> /dev/null) -std=c++11 -o $@

# Network code for analysed random point
%.cpp:%_analysed_point.json %.net
	$(call act, cnn-backend -p $< -n $*.net --halide-code $@ $(BACKEND_FLAGS))

# Translation of caffe to tool network model
%.net %.dot:%.prototxt %.caffemodel
	$(call act, cnn-frontend --caffe-deploy $< --caffe-model $*.caffemodel --write-network-dotfile $*.dot --write-model $@ $(FRONTEND_FLAGS))

# Analysed random point
%_analysed_point.json:%_point.json
	$(call act, cnn-opt -n $*.net -p $< -o $@ $(OPT_FLAGS))

# Random schedule point
%_point.json:%.net
	$(call act, cnn-dse --dse-max-fused-layers=1 --dse-save-points $@ -n $< --dse-strategy random $(DSE_FLAGS))

# Naive points for this network under restrictions of DSE flags
%_naive.json:%.net
	$(call act, cnn-dse --dse-max-fused-layers=1 --dse-save-points $@ -n $< --dse-strategy naive $(DSE_FLAGS))

# Pareto points for this network under restrictions of DSE flags
%_points.json:%.net
	$(call act, cnn-dse --dse-max-fused-layers=1 --dse-save-points $@ -n $< $(DSE_FLAGS))

# Plot of pareto points
%_plot.pdf:%_points.json
	$(call act, cnn-plot -s -b $@ -c $< -l $* )

# Code of schedule "%" of the pareto points with tracing and profiling enabled
trace_%.cpp:$(NET)_points.json $(NET).net
	$(call act, cnn-backend -p $< -n $(NET).net -i $* --halide-code $@ $(BACKEND_FLAGS) --halide-trace-code --halide-profile-code)

# Traced accesses and memory sizes of schedule "%"
accesses_%.csv memsize_%.csv:trace_%.exe $(INPUT_FILES)
	$(call act, ./$< $(INPUT_FILES) |& halide-access-count -o accesses_$*.csv --log-level=INFO |& halide-mem-size -o memsize_$*.csv --log-level=INFO)

# Command file to trace accesses for all pareto schedules
%_remote.cmd:%_points.json
	@rm -f $@; for i in $(shell python -c "import json; print ' '.join(map(str, range(len(json.loads(open('$<').read())))))"); do echo "nice -n 10 make -C $(CURDIR) memsize_$$i.csv" >> $@; done

# Generate all accesses on remote servers (implicitly generates all accesses_id.csv and memsize_id.csv)
%_remote_done:%_remote.cmd $(INPUT_FILES)
	$(call act, $(BINDIR)/driver.py -n $(shell ls $(BINDIR)/servers.conf > /dev/null && echo "-s $(BINDIR)/servers.conf") -c $< && touch $@)

# Combine measurements
%_measured.json:%_remote_done
	$(call act, $(BINDIR)/collect_measurements.py -a accesses_* -b memsize_* -o $@)

# Plot Modeled vs Baseline points
%_plot_model_vs_baseline.pdf:%_points.json %_naive.json
	$(call act, cnn-plot -s -b $@ -c $^ -l $*_modeled $*_baseline )

# Plot Modeled vs Measured points
%_plot_model_vs_measured.pdf:%_points.json %_measured.json
	$(call act, cnn-plot -s -b $@ -c $^ -l $*_modeled $*_measured )

# Plot Modeled vs Measured points vs Naive points
%_plot_model_vs_measured_vs_baseline.pdf:%_points.json %_measured.json %_naive.json
	$(call act, cnn-plot -s -b $@ -c $^ -l $*_modeled $*_measured $*_baseline )

# List of all generated files
TGT_SUFFIXES+=.net .dot _point.json _naive.json _analysed_point.json .cpp .exe _points.json _plot.pdf _remote.cmd _remote_done _measured.json _plot_model_vs_measured.pdf _plot_model_vs_baseline.pdf _plot_model_vs_measured_vs_baseline.pdf _output.txt
GENERATED+=$(foreach sufx, $(TGT_SUFFIXES), $(addsuffix $(sufx), $(NET)))

# Generic plot target
plot:$(addsuffix _plot.pdf, $(NET)) ## Plot pareto front after DSE

# Plot modelled pareto + naive points
plot_baseline:$(addsuffix _plot_model_vs_baseline.pdf, $(NET)) ## Plot pareto front after DSE and the baseline

# Verify target
verify:$(addsuffix _plot_model_vs_measured_vs_baseline.pdf, $(NET)) ## Verify DSE by implementing points and measuring buffers. Note: cal take a long time!

# Keep everything generated
PRECIOUS+=$(GENERATED)
.PRECIOUS:$(PRECIOUS)

.PHONY:clean
CLEAN+=$(GENERATED)
clean: ## clean generated files
	rm -f $(CLEAN) ./*.bin ./*_buf.txt ./accesses_*.csv ./memsize_*.csv trace_*.cpp trace_*.exe


###########
#
# Cleaning of the Virtual Env
#
.PHONY:realclean
realclean:clean ## Clean everything including the virtual environment leaving a clean repository
	rm -rf $(VENV) $(ACT)
