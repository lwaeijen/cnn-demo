CNN Tool Demo
-------------

Demonstration repo to showcase halide code generation using the CNN implementation tool.
The central makefile contains the generic build rules which use the CNN tool.
All the subdirectories with the exception of util contain a makefile which fetches a pretrained network from the web (if not contained in the folder already).
Using the randomsearch strategy, a random schedule is selected, and the halide code is generated according to this schedule.
The code is compiled and called from main.cpp to evaluate the network.
The output is then checked for correctness.

The "utils" folder contains a python script which can be used to perform the inference using python and caffe.
Note that caffe should be built and installed with the python extensions for this to work.

Installation & Usage
--------------------
To install the CNN tools simply execute ```make``` in the main directory once.
This will setup a virtual environment and fetch all the required dependencies.

To execute a network, cd to the subdir and execute ```make``` again.
This will automatically download, schedule, compile and execute the selected network.

For a design space exploration of the network implementation options execute ```make plot``` in the directoy of the network.
This will generate a pdf file with the pareto front.
Note that to speed up the default DSE, the --dse-no-tiling flag is passed by the root Makefile to disable different tile sizes.
For a full exploration comment this flag in the main Makefile.

To verify the DSE points found be the models by measuring the accesses and buffer size of implementations execute ```make verify```
Note that this command may require a lot of time, depending on the number of points.
To speed things up, these verifications can be executed on remote servers using the same filesystem.
Additional servers can be configured in the utils/servers.conf file.
To keep the file system synchronised the 'sshfs' tool can be an ad hoc solution.
If no servers are specified, the localhost and local machine will be used.
Please make sure your user has ssh access to the local machine in this case.

Extra
-----
Once the virtual environment is activated by running ```source activate``` after ```make``` has completed in the root directory, the ```compare``` tool will be available.
This tool can be used to quickly compare predicted and measured values for the individual points of the DSE.
To use change into the directory that contains the predicted network_points.json and the measured accesses*.csv and memsize*.csv files.
Here, execute ```compare <schedule_id>```, where schedule_id is the index of the point being compared.

Known Issues
------------
In it's current implementation, the halide code for the network is placed into one large function.
On some systems this may increase the stack size beyond the soft limit, and a segfault occurs.
In case you get a segfault immediately after starting the compiled binary, most likely it's a problem of a too small maximum stack size.
You can check your limits on linux with "ulimit -s", and if desired increase with "ulimit -s <new_number>"
