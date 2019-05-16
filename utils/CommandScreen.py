#!/usr/bin/env python
import curses
from threading import Thread, Lock
import sys
from time import sleep
from collections import deque

class CommandScreen(Thread):

    topbar_attr = curses.A_BOLD | curses.A_UNDERLINE
    menu_attr = curses.A_NORMAL

    def __init__(self):
        Thread.__init__(self)
        self.__stop=False
        self.daemon=True
        self.refresh =True
        self.l = Lock()
        self.reset_screen=True

        self.__lmenu_items=[]
        self.__selected=0
        self.__lmenu_xoffset=0

        self.__text_buffers=[]
        self.__term_scroll=[]
        self.__line_buffer_size=1024

        self.focus='lmenu'

        #start the thread
        self.__init_done=False
        self.start()

        #wait for first window to be drawn, otherwise commands will fail
        while not self.__init_done:
            sleep(0.01)

    def add_tab(self, name):
        with self.l:
            self.__lmenu_items+=[name]
            self.reset_screen=True
            self.__text_buffers+=[(Lock(), deque(maxlen=self.__line_buffer_size))]
            self.__term_scroll+=[0]
            #return handle
            return len(self.__lmenu_items)-1

    def print_text(self, handle, text):
        lock, buf = self.__text_buffers[handle]

        #cut new text in lines of width that match the current terminal
        width=self.term_width

        #first get lock on this text buffer
        with lock:
            cnt=0
            for line in text.split('\n'):
                for subline_start in range(0,len(line), width):
                    subline_end = min(subline_start+width, len(line))
                    subline = line[subline_start:subline_end]

                    #add sublines to the buffer
                    buf.append(subline)
                    cnt+=1

            #adjust scroll offset
            if self.__term_scroll[handle]!=0:
                self.__term_scroll[handle]+=cnt

        #ask for a screen update
        if handle == self.__selected:
            self.__draw_term()

    def run(self):
        #start curses loop
        curses.wrapper(self.loop)

    def __reset_screen(self):

        #Clear the screen
        self.scr.clear()

        #get new width and height
        height,width = self.scr.getmaxyx()
        self.height=height
        self.width=width

        #set coordinates of the top bar
        self.topbar_x = 1
        self.topbar_y = 1
        self.topbar=curses.newwin(1,self.width,self.topbar_y, self.topbar_x)

        #init border for lmenu
        self.lmenu_border_width=22
        self.lmenu_border_y=self.topbar_y+1
        self.lmenu_border_x=self.topbar_x
        self.lmenu_border=curses.newwin(0,self.lmenu_border_width,self.lmenu_border_y,self.lmenu_border_x)
        self.lmenu_border.box()

        #freeze async operations to the lmenu items
        with self.l:
            #save max width of the items we're displaying
            self.__lmenu_item_max_width=(max(map(len, self.__lmenu_items)) if len(self.__lmenu_items) else 1)

            #save cnt that we've built the pad for. If more are added (async) this reset function needs to be called to update
            self.__lmenu_item_cnt=len(self.__lmenu_items)


        #init the left menu at the correct size
        self.lmenu_width=self.lmenu_border_width-4
        self.lmenu_y=self.lmenu_border_y+1
        self.lmenu_x=self.lmenu_border_x+2
        self.lmenu_height=self.height-self.lmenu_y-2
        self.lmenu = curses.newpad(max(1,self.__lmenu_item_cnt),max(self.lmenu_width, self.__lmenu_item_max_width+1))


        #draw the left menu
        self.__draw_lmenu()

        #init border for the terminal
        self.term_border_x=self.lmenu_border_x+self.lmenu_border_width+2
        self.term_border_y=self.lmenu_border_y
        self.term_border_width=self.width-self.term_border_x
        self.term_border_height=self.height-self.term_border_y
        self.term_border=curses.newwin(0,self.term_border_width,self.term_border_y, self.term_border_x)
        self.term_border.box()

        #init terminal
        self.term_width=self.term_border_width-4
        self.term_height=self.term_border_height-2
        self.term_x=self.term_border_x+2
        self.term_y=self.term_border_y+1
        self.term=curses.newwin(self.term_height,self.term_width,self.term_y, self.term_x)
        self.__draw_term()

        #finally draw the various windows
        self.__draw_topbar()

        #request a refresh
        self.refresh=True

    def __draw_topbar(self):
        self.topbar.clear()

        attr=self.topbar_attr|curses.A_REVERSE if self.focus == 'lmenu' else self.topbar_attr
        text='Select:'
        self.topbar.addstr(0, max(0,(self.lmenu_border_width-len(text))/2),text, attr)

        attr=self.topbar_attr|curses.A_REVERSE if self.focus == 'term' else self.topbar_attr
        text='Terminal' if not self.__selected < len(self.__lmenu_items) else self.__lmenu_items[self.__selected]
        self.topbar.addstr(0, self.term_x+max(0,(self.term_border_width-len(text))/2),text, attr)

        #request refresh
        self.refresh=True

    def __draw_term(self):
        if self.__selected < len(self.__text_buffers):
            self.term.clear()
            lock, buf = self.__text_buffers[self.__selected]
            scroll_offset = self.__term_scroll[self.__selected]
            with lock:
                for idx in range(self.term_height):
                    buf_idx=idx+scroll_offset
                    if buf_idx>=len(buf):
                        break
                    line=buf[-1*(buf_idx+1)]
                    line=line[0:min(self.term_width-1, len(line))]
                    self.term.addstr(self.term_height-1-idx, 0, line)

            #request refresh
            self.refresh=True

    def __draw_lmenu(self):
        with self.l:
            for idx in range(self.__lmenu_item_cnt):
                text = self.__lmenu_items[idx]
                attr= self.menu_attr
                if idx==self.__selected:
                    attr |= curses.A_REVERSE
                self.lmenu.addstr(idx, 0, text, attr )
            #request refresh
            self.refresh=True

    def loop(self, scr):
        #set screen object to this instance
        self.scr = scr

        #disable cursor
        curses.curs_set(False)

        #make getch non-blocking
        scr.nodelay(1)

        #loop processing input until we need to stop
        while not self.__stop:


            #get key
            c=scr.getch()

            #quit
            if c == ord('q'):
                return 0

            #home key
            if c == curses.KEY_HOME:
                if self.focus == 'lmenu':
                    self.__selected=0
                    self.__draw_lmenu()
                    self.__draw_term()
                    self.__draw_topbar()
                else:
                    lock, buf = self.__text_buffers[self.__selected]
                    with lock:
                        self.__term_scroll[self.__selected]=max(0,len(buf)-self.term_height)
                    self.__draw_term()

            #end key
            elif c == curses.KEY_END:
                if self.focus == 'lmenu':
                    self.__selected=len(self.__lmenu_items)-1
                    self.__draw_lmenu()
                    self.__draw_term()
                else:
                    lock, buf = self.__text_buffers[self.__selected]
                    with lock:
                        self.__term_scroll[self.__selected]=0
                    self.__draw_term()

            #page up
            elif c == curses.KEY_PPAGE:
                if self.focus == 'term':
                    lock, buf = self.__text_buffers[self.__selected]
                    with lock:
                        self.__term_scroll[self.__selected]=min(max(0,len(buf)-self.term_height),self.__term_scroll[self.__selected]+self.term_height)
                    self.__draw_term()

            #page down
            elif c == curses.KEY_NPAGE:
                if self.focus == 'term':
                    lock, buf = self.__text_buffers[self.__selected]
                    with lock:
                        self.__term_scroll[self.__selected]=max(0,self.__term_scroll[self.__selected]-self.term_height)
                    self.__draw_term()


            #arrow up
            elif c == curses.KEY_UP or c == ord('k'):
                if self.focus == 'lmenu':
                    self.__selected=max(0,self.__selected-1)
                    self.__draw_lmenu()
                    self.__draw_term()
                    self.__draw_topbar()
                else:
                    lock, buf = self.__text_buffers[self.__selected]
                    with lock:
                        self.__term_scroll[self.__selected]=min(max(0,len(buf)-self.term_height),self.__term_scroll[self.__selected]+1)
                    self.__draw_term()

            #arrow down
            elif c == curses.KEY_DOWN or c == ord('j'):
                if self.focus == 'lmenu':
                    self.__selected=min(len(self.__lmenu_items)-1,self.__selected+1)
                    self.__draw_lmenu()
                    self.__draw_term()
                    self.__draw_topbar()
                else:
                    lock, buf = self.__text_buffers[self.__selected]
                    with lock:
                        self.__term_scroll[self.__selected]=max(0,self.__term_scroll[self.__selected]-1)
                    self.__draw_term()

            #arrow right
            elif c == curses.KEY_RIGHT or c == ord('l'):
                if self.focus == 'lmenu':
                    self.__lmenu_xoffset=min(self.__lmenu_item_max_width-self.lmenu_width+2,self.__lmenu_xoffset+1)
                    self.refresh=True

            #arrow left
            elif c == curses.KEY_LEFT or c == ord('h'):
                if self.focus == 'lmenu':
                    self.__lmenu_xoffset=max(0,self.__lmenu_xoffset-1)
                    self.refresh=True

            #TAB
            elif c ==ord('\t'):
                self.focus = 'lmenu' if not self.focus=='lmenu' else 'term'
                self.__draw_topbar()

            #resize of the parent window
            elif c == curses.KEY_RESIZE:
                self.reset_screen=True

            #give the CPU some breathing room
            else:
                #reset / init the screen
                if self.reset_screen:
                    self.__reset_screen()
                    scr.noutrefresh()
                    self.lmenu_border.noutrefresh()
                    self.term_border.noutrefresh()
                    self.refresh=True
                    with self.l:
                        self.reset_screen=False

                #refresh if required
                if self.refresh:
                    self.topbar.nooutrefresh()
                    self.lmenu.noutrefresh(self.__selected-(self.lmenu_height),self.__lmenu_xoffset,self.lmenu_y,self.lmenu_x,self.lmenu_y+self.lmenu_height,self.lmenu_width)
                    self.term.noutrefresh()
                    curses.doupdate()
                    with self.l:
                        self.refresh=False
                        self.__init_done=True
                else:
                    #absolutely nothing to do, rest for a while
                    sleep(0.05)


    def stop(self):
        #force a stop
        self.__stop=True
        #wait max 5 seconds for all threads to terminate
        self.join(timeout=5)

    def join(self, timeout=-1):
        try:
            while self.isAlive():
                super(CommandScreen, self).join(1)
                if timeout>0:
                    timeout-=1
                if timeout==0:
                    break
        except:
            self.stop()


if __name__ == "__main__":
    scr = CommandScreen()
    for i in range(40):
        scr.add_tab("menu item "+str(i))

    for i in range(5000):
        scr.print_text(0,"lorem ipsum carpe diem etcetera %d\n"%(i))
        scr.print_text(2,"carpe diem %d\n"%(i))
        sleep(0.1)
    scr.join()
