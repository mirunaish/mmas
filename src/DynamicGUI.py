import threading
import time
from tkinter import ttk
from PIL import ImageTk
from PIL import Image


# Created by GUI, contains the status bar and the preview windows
# Handles the "dynamic" elements of the GUI separately to prevent circular imports
# Accessed by both the GUI and the scripts
class DynamicGUI:

    # static methods

    # resize an image in preparation for displaying it in the preview window
    @staticmethod
    def resize(image):
        x, y = image.size
        ratio = min(450 / x, 400 / y)  # max size is 450x400
        x = int(x * ratio)
        y = int(y * ratio)
        image = image.resize((x, y))
        return ImageTk.PhotoImage(image=image, size=(x, y))

    # get a resized image given a path
    @staticmethod
    def open_resized_image(path):
        DynamicGUI.resize(Image.open(path))

    # preview window common parts
    class PreviewWindow:
        def __init__(self, master, index):
            self.name = index
            self.window = ttk.PanedWindow(master=master, name=str(index))
            self.window.columnconfigure(0, weight=1, uniform="y")
            self.window.columnconfigure(1, weight=2, uniform="y")

            self.status_label = ttk.Label(master=self.window, text="loading...")
            self.status_label.grid(column=0, row=0, sticky="nwe")

            self.progress_bar = ttk.Progressbar(master=self.window)
            self.progress_bar.grid(column=1, row=0, sticky="nwe")

            self.sep = ttk.Separator(master=self.window, orient="horizontal")
            self.sep.grid(column=2, row=0, sticky="new")

            self.container = ttk.Frame(master=self.window)
            self.container.grid(column=0, row=1, sticky="nesw", columnspan=2)

        # change text in label
        def update(self, text):
            self.status_label.configure(text=text)

        # set progress bar progress
        def progress(self, amount):  # amount between 0 and 100
            self.progress_bar.configure(value=amount)

        def destroy(self):
            self.window.destroy()

    def __init__(self, root):
        # preview panel will hold a notebook of windows that contain previews of running threads
        # preview probably misnomer; more of an in-progress-view
        self.preview_panel = ttk.Notebook(master=root)
        self.preview_panel.grid(row=0, column=4, sticky="nsew")

        # status panel holds a status message
        status_panel = ttk.Frame(master=root)
        status_panel.grid(row=2, column=0, columnspan=5, sticky="sew")
        self.status_message = ttk.Label(master=status_panel)
        self.status_message.grid(column=0, row=0, sticky="w")

        self.tabs = {}  # dictionary
        self.files = set()

        # all threads share the same DynamicGUI instance
        self.file_lock = threading.Lock()  # only one thread can access the file set at the same time
        self.tab_lock = threading.Lock()  # only one thread can access the tab dictionary at the same time
        self.status_waiting_threads = set()  # threads waiting to clear status. when one is added the others are removed

    # return true if file is currently being written to by another thread
    def file_locked(self, file):
        self.file_lock.acquire(blocking=True)
        value = self.files.__contains__(file)
        self.file_lock.release()
        return value

    # add file to set of files currently in use
    def lock_file(self, file):
        self.file_lock.acquire(blocking=True)
        self.files.add(file)
        self.file_lock.release()

    # add file to set of files currently in use
    def unlock_file(self, file):
        self.file_lock.acquire(blocking=True)
        self.files.remove(file)
        self.file_lock.release()

    def new_tab(self, command, path, file):
        # only one thread can change the file set at the same time
        self.file_lock.acquire(blocking=True)
        # and only one thread can add/remove a tab at the same time
        self.tab_lock.acquire(blocking=True)

        index = 0  # must be defined in this scope
        # find first unused name
        for index in range(len(self.tabs)+1):  # len(self.tabs) will realistically be 0-3 at any given time
            if not self.tabs.__contains__(index):
                break  # break out of the for loop

        # add a new paned window in the preview panel
        preview = self.PreviewWindow(self.preview_panel, index)
        self.tabs.update({index: preview})
        self.preview_panel.add(preview.window, text=command + ": " + file)  # text is the tab name

        # select this new tab
        self.preview_panel.select(str(index))

        # mark file as in-use so nobody else tries to write to it at the same time
        self.files.add(path+"\\"+file)

        self.file_lock.release()
        self.tab_lock.release()

        return preview

    def remove_tab(self, task):
        self.tab_lock.acquire()
        # destroy the preview window with this task name
        self.preview_panel.forget(str(task))
        self.tabs.get(task).destroy()
        # remove this tab from the dictionary
        self.tabs.pop(task)
        self.tab_lock.release()

    # update the status message, remove it after 5 seconds of no updates
    def update_status(self, text, err=False):  # if err is True label text will be red

        # thread that waits for 5 seconds and then clears the status message
        class WaitingThread(threading.Thread):
            def __init__(nested_self):
                super().__init__()
                nested_self.override = False  # will be True if someone else updates status while i'm waiting

            def run(nested_self):
                self.status_waiting_threads.add(nested_self)
                time.sleep(5)
                if not nested_self.override:  # only clear if i have not been overriden
                    self.clear_status()  # this self is the self of the update_status method and is a DynamicGUI
                self.status_waiting_threads.remove(nested_self)  # i'm done, remove myself

        # if any threads are waiting to delete the status message, tell them they've been overriden
        for t in self.status_waiting_threads:
            t.override = True

        ttk.Style().configure("Color.TLabel", foreground="red" if err else "black")

        # update the status message, then start the thread that tries to clear it after 5 seconds
        self.status_message.configure(text=text, style="Color.TLabel")
        WaitingThread().start()

    def clear_status(self):
        self.status_message.configure(text="")
