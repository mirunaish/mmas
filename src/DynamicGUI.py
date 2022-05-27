import threading
import time
from tkinter import ttk
from PIL import ImageTk
from PIL import Image
from src.exceptions import FileLockedError


# preview window common parts
class PreviewWindow:

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
        return PreviewWindow.resize(Image.open(path))

    def __init__(self, master, name):
        self.name = name
        self.window = ttk.PanedWindow(master=master, name=str(name))
        self.window.columnconfigure(0, weight=1, uniform="y")
        self.window.columnconfigure(1, weight=2, uniform="y")

        self.status_label = ttk.Label(master=self.window, text="loading...")
        self.status_label.grid(column=0, row=0, sticky="nwe")

        self.progress_bar = ttk.Progressbar(master=self.window)
        self.progress_bar.grid(column=1, row=0, sticky="nwe")

        sep = ttk.Separator(master=self.window, orient="horizontal")
        sep.grid(column=2, row=0, sticky="new")

        # script config_preview will put its labels and whatnot in this container
        self.container = ttk.Frame(master=self.window)
        self.container.grid(column=0, row=1, sticky="nesw", columnspan=2)

        # default label for placing text or an image
        self.main = ttk.Label(master=self.container, text="loading...")
        self.main.grid(row=0, column=0)

    # change text in status label (next to progress bar)
    def progress_update(self, text):
        self.status_label.configure(text=text)

    # set progress bar progress
    def progress_amount(self, amount):  # amount between 0 and 100
        self.progress_bar.configure(value=amount)

    # put an image in the main label. can use either image or image_path but not both
    def put_image(self, image=None, image_path=None):
        if image is not None:
            image = self.resize(image)
        elif image_path is not None:
            image = self.open_resized_image(image_path)

        # remove text and put image
        self.main.configure(text="", image=image)
        self.main.pointer = image  # prevent the image from getting garbage collected

    # put text in the main label
    def put_text(self, text):
        # remove image and put text
        self.main.configure(text=text, image=None)
        # allow garbage collection of previous image
        self.main.pointer = None

    def destroy(self):
        self.window.destroy()


# Created by GUI, contains the status bar and the preview windows
# Handles the "dynamic" elements of the GUI separately to prevent circular imports
# Also handles locking and unlocking resources for multithreading
# Accessed by both the GUI and the scripts
class DynamicGUI:

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

        # all threads share the same DynamicGUI instance
        self.tab_lock = threading.Lock()  # only one thread can access the tab dictionary at the same time
        self.status_waiting_threads = set()  # threads waiting to clear status. when one is added the others are removed

    # create a new preview tab
    def new_tab(self, script, file):
        # only one thread can add/remove a tab at the same time
        self.tab_lock.acquire(blocking=True)

        name = 0  # must be defined in this scope
        # find first unused "name" - names are just numbers in this case
        for name in range(len(self.tabs)+1):  # len(self.tabs) will realistically be 0-3 at any given time
            if name not in self.tabs:
                break  # out of the for loop

        # add a new paned window in the preview panel
        preview = PreviewWindow(self.preview_panel, name)
        self.tabs.update({name: preview})
        self.preview_panel.add(preview.window, text=script + ": " + file)  # text is the tab name

        # select this new tab
        self.preview_panel.select(str(name))

        self.tab_lock.release()

        return preview

    def remove_tab(self, name):
        self.tab_lock.acquire()
        # destroy the preview window with this task name (some number)
        self.preview_panel.forget(str(name))
        self.tabs.get(name).destroy()
        # remove this tab from the dictionary
        self.tabs.pop(name)
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
                if not nested_self.override:  # only clear if i have not been overridden
                    self.clear_status()  # this self is the self of the update_status method and is a DynamicGUI
                self.status_waiting_threads.remove(nested_self)  # i'm done, remove myself

        # if any threads are waiting to delete the status message, tell them they've been overridden
        for t in self.status_waiting_threads:
            t.override = True

        ttk.Style().configure("Color.TLabel", foreground="red" if err else "black")

        # update the status message, then start the thread that tries to clear it after 5 seconds
        self.status_message.configure(text=text, style="Color.TLabel")
        WaitingThread().start()

    def clear_status(self):
        self.status_message.configure(text="")
