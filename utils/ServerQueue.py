#!/usr/bin/env python
from threading import Thread, Lock
from time import sleep
try:
    #python3
    from queue import Queue, Full
except:
    #python 2
    from Queue import Queue, Full
import paramiko
import logging

from CommandScreen import CommandScreen

#set paramiko to only warnings to avoid a lot of clutter
logging.getLogger("paramiko").setLevel(logging.WARNING)

class ServerQueue(object):
    #Was supposed to be a direct subclass of queue but in python queue has some issues and can not be subclassed -_-

    def __init__(self, servers, persistent=True, **kwargs):

        #if persistent, tasks with a non-zero exit value will be requeued for processing
        self.persistent=persistent

        #A timeout is given to hosts that fail a task
        #Note that if there is a problem with the tasks, this can lead to a lot of idle workers and a queue filled with broken tasks!
        self.penalize_failing_hosts=True

        #create logger
        #self.log=logging.getLogger('ServerQueue')
        self.loglevel=logging.getLogger().getEffectiveLevel()
        self.scr = CommandScreen()
        self.main_handle = self.scr.add_tab("Main")

        #notify user
        self.info("Starting Server Queue")

        #init Queue to hold tasks
        self.Q=Queue(maxsize=len(servers)*16, **kwargs)

        #keep track of how many tasks still need to be processed
        self.pending_tasks=0
        self.pending_tasks_lock=Lock()

        #Create list of workers
        self.workers=[ Thread(target=self.worker, args=server_info) for server_info in servers]

        #Set workers to Daemon mode to ensure they are terminated when the main thread exits
        [ w.setDaemon(True) for w in self.workers]

        #list of all ssh clients / connections
        self.client_lock=Lock()
        self.clients=[]

    def print_main(self,msg):
        self.scr.print_text(self.main_handle, msg)

    def debug(self, msg):
        if self.loglevel<=logging.DEBUG:
            self.print_main('COW: %d, %d'%(self.loglevel, logging.DEBUG))
            self.print_main('DBG:  '+msg)

    def info(self, msg):
        if self.loglevel<=logging.INFO:
            self.print_main('INFO: '+msg)

    def warning(self, msg):
        if self.loglevel<=logging.WARNING:
            self.print_main('WARN: '+msg)

    def error(self, msg):
        if self.loglevel<=logging.ERROR:
            self.print_main('ERR: '+msg)

    def __add_client(self, conn):
        with self.client_lock:
            self.clients.append(conn)

    def __start_workers(self):
        #open connections to all servers
        self.active=True
        [ w.start() for w in self.workers]

    def __getattr__(self, name):
        try:
            #subclass emulation, pass missing attributes (==method calls) to Q first
            return getattr(self.Q, name)
        except:
            raise AttributeError

    def worker(self, host, username):
        #add tab to command screen
        scr_handle=self.scr.add_tab(host)

        #setup paramiko ssh client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.__add_client(client)

        #exponential back off for retrying to connect start at 1 second
        backoff=8

        #failed task penalty
        penalty=0

        def line_buffered(f):
            #yield buffered lines
            remaining=''
            while not f.channel.exit_status_ready():
                output = f.read(256)

                #prefix output with whatever was remaining from previous iteration
                output = remaining + output

                #find the last newline
                newline_idx=output.rfind('\n')

                #everything after the last new line will be kept until next iteration
                remaining=output[newline_idx+1:]

                #if there was at least a valid newline, we can yield the output until the last newline
                if newline_idx!=-1:
                    yield output[0:newline_idx]
                    #for line in output[0:newline_idx].split('\n'):
                    #    yield line

            #read whatever is left
            yield remaining + f.read()

        while self.active:
            try:
                self.debug('Trying to connect to: %s'%(host))
                client.connect(host, username=username)
                self.debug('Established connection to: %s'%(host))
                backoff=8

                #Keep processing tasks (unless there is an exception)
                while self.active:

                    task = self.get()
                    try:
                        #Execute task on server
                        self.info(host+': '+task)
                        stdin, stdout, stderr = client.exec_command(task)

                        #print stdout continuously
                        for line in line_buffered(stdout):
                            if line.strip():
                                #self.info('-'*20+'\nHOST: '+host+':\n'+line+'\n'+'-'*20)
                                self.scr.print_text(scr_handle, line)

                        #log stderr if required
                        if stdout.channel.recv_exit_status()!=0:
                            self.error('Host "'+host+'" had an error, see log of this host\n')
                            self.scr.print_text(scr_handle, stderr.read().strip())


                            #if we are persistent, we requeue tasks with a non-zero exit value
                            if self.persistent:
                                self.warning("Host %s failed task %s. REQUEUEING because PERSISTANT is set"%(host, task))
                                self.put(task)

                                #hosts that fail a task get exponential penalty
                                if penalty==0:
                                    penalty=1
                                else:
                                    penalty*=2

                                #max penalty of 10 minutes
                                penalty=min(penalty,600)
                                self.warning("Host %s failed task, timeout of %d seconds"%(host, penalty))
                        else:
                            penalty=0

                    except:
                        #if we fail whilst executing the task,
                        #put it back on the queue and report the current one as done
                        self.put(task)
                        self.task_done()

                        #Assume we failed due to bad connection, so close the connection
                        #And pass to higher level try to trigger a reconnect
                        client.close()
                        raise paramiko.ssh_exception.SSHException

                    #signal we processed our task
                    self.task_done()

                    #if our worker host failed we apply a penalty before accepting new tasks
                    if self.penalize_failing_hosts:
                        #exponential backoff, but keep polling the active property
                        for _ in xrange(penalty):
                            if not self.active:
                                return
                            sleep(1)

            except (
                paramiko.ssh_exception.AuthenticationException,
                paramiko.ssh_exception.NoValidConnectionsError,
                paramiko.ssh_exception.SSHException
            ):
                if self.active:
                    self.warning('Failed to connect to: %s'%(host))
                    self.warning('Retrying to connect to %s in %d seconds'%(host, backoff))

                #exponential backoff, but keep polling the active property
                for _ in xrange(backoff):
                    if not self.active:
                        return
                    sleep(1)
                backoff*=2
                #maximum backoff of 10 minutes
                backoff=min(backoff, 600)

    def __enter__(self):
        self.__start_workers()
        return self

    def __exit__(self, exc_type, exc_value, traceback):

        #Tell all worker threads to stop gracefully
        self.active=False

        #close all connections
        for client in self.clients:
            client.close()

        #stop the command screen gracefully
        self.scr.stop()


    def join(self):
        #Regular Queue.join can not be interrupted
        #We use this trick to allow Keyboard interrupt for example
        while True:
            with self.pending_tasks_lock:
                if self.pending_tasks==0:
                    return
            sleep(1)

    def wait_user_exit(self, msg):
        #go ahead and already close the connections
        self.active=False
        for client in self.clients:
            client.close()

        #wait for user to terminate the command screen
        self.info(msg)

        #wait for user to terminate
        while self.scr.isAlive():
            sleep(1)

    #Override put and task done to do own administration of pending tasks
    def put(self, item):
        with self.pending_tasks_lock:
            self.pending_tasks+=1
        self.Q.put(item)

    def task_done(self):
        with self.pending_tasks_lock:
            self.pending_tasks-=1



if __name__ == '__main__':
    #disable paramiko logging by default
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    #create ServerQueue
    with ServerQueue() as SQ:
        #Issue all the commands
        for Id in range(60):
            cmds=[
                'cd cnn-experiments',
                'source activate',
                'cd intralayer',
                'make check ID=%d'%(Id)
            ]
            cmd='bash -c "%s"'%(' && '.join(cmds))
            cmd="hostname && date"

            #put command in the queue
            SQ.put(cmd)

        #Wait for all commands to be processed
        #logging.debug("Waiting for all tasks to be completed")
        SQ.join()

        #wait for user to terminate GUI
        SQ.wait_user_exit("All tasks completed! Press 'q' to exit")
