#!/usr/bin/env python
import sys
from ServerQueue import ServerQueue
import logging
import argparse
import os
import pwd
from ConfigParser import SafeConfigParser as ConfigParser

#reasonalbe portable way to get name of current user
def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

#Construct the parser
parser = argparse.ArgumentParser(description="Intra-layer experimentation driver")

#Add GENERIC OPTIONS to parser
_LOG_LEVEL_STRINGS = ['ERROR','WARNING', 'INFO', 'DEBUG']
def _log_level_string_to_int(log_level_string):
    if not log_level_string in _LOG_LEVEL_STRINGS:
        message = 'invalid choice: {0} (choose from {1})'.format(log_level_string, _LOG_LEVEL_STRINGS)
        raise argparse.ArgumentTypeError(message)
    log_level_int = getattr(logging, log_level_string, logging.ERROR)
    # check the logging log_level_choices have not changed from our expected values
    assert isinstance(log_level_int, int)
    return log_level_int

parser.add_argument('--log-level',
	default='INFO',
	dest='log_level',
	type=_log_level_string_to_int,
	nargs='?',
	help='Set the logging output level. {0}'.format(_LOG_LEVEL_STRINGS),
)

#intralayer arguments
parser.add_argument('-c', '--cmd', dest='cmd', required=False, action='store', default=None,
    help="File with commands to execute on remote servers. Each line is executed on a server."
)

parser.add_argument('-s', '--servers', dest='server_conf', required=False, action='store', default=None,
    help="Path to config file with servers to use. When not specified localhost with the current username will be used"
)

parser.add_argument('-n', '--no-wait', dest='nowait', required=False, action='store_true', default=False,
    help="Do not wait for user input to terminate after all jobs are processed"
)

parser.add_argument('-p', '--not-persistent', dest='persistent', required=False, action='store_false', default=True,
    help="Skip failed jobs"
)

# Parse arguments
args = parser.parse_args()

#Construct the logger
logging.basicConfig(level=args.log_level, format="%(message)s")
logger = logging.getLogger()

#Get servers to use, default is localhost with current username
if not args.server_conf:
    servers=[( 'localhost', get_username())]
else:
    cp=ConfigParser()
    cp.read(args.server_conf)
    servers=[]
    for sec in cp.sections():
        if 'connections' not in cp.options(sec):
            servers+=[(cp.get(sec, 'host'), cp.get(sec, 'user'))]
        else:
            #if multiple connections are specified, we add N times to encourage concurrency
            for con_id in range(int(cp.get(sec,'connections'))):
                servers+=[(cp.get(sec, 'host'), cp.get(sec, 'user'))]

#create ServerQueue
with ServerQueue(servers, persistent=args.persistent) as SQ:

    #Issue all the commands
    if not args.cmd:
        #If not commands are specified, run 'hostname' for number of servers
        #NOTE: no guarantee all will be executed by different servers!
        for _ in range(len(servers)):
            SQ.put('hostname')
    else:
        with open(args.cmd, 'rt') as f:
            for cmd in f.readlines():
                #put command in the queue
                SQ.put(cmd.strip('\n'))

    #Wait for all commands to be processed
    logging.debug("Waiting for all tasks to be completed")
    SQ.join()

    #wait for user to terminate GUI
    if not args.nowait:
        SQ.wait_user_exit("All tasks completed! Press 'q' to exit")
