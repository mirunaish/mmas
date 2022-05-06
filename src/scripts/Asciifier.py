import threading
from os.path import isdir
from time import sleep
from tkinter import ttk
import random
from src.DynamicGUI import DynamicGUI
from PIL import Image, ImageChops


# given an image turn it into a string
class Asciifier(threading.Thread):
    def __init__(self, gui, image_path, dest_dir_path, resolution, static, white_on_black):
        super().__init__(daemon=True)

        self.command = "Asciify"  # will appear in the preview window tab

        # if path was given with slashes, convert to backslash path
        self.image_path = image_path.replace('/', '\\')  # the image to be transformed
        self.dest_dir_path = dest_dir_path.replace('/', '\\')  # the path to the folder where the mp3 should be placed
        if self.dest_dir_path[len(self.dest_dir_path) - 1] == '\\':  # if last character is a backslash
            self.dest_dir_path = self.dest_dir_path[:-1]  # remove last backslash character

        # get the name of the image from the path
        self.image_name = self.image_path.split("\\").pop()  # split into path parts, get last part (filename)
        self.image_name = self.image_name.split(".")[0]  # remove file extension

        self.result_file_name = self.image_name + " - asciified.txt"  # the destination file name + extension

        self.static = static
        self.white_on_black = white_on_black
        self.resolution = 50 if resolution == 'small (50)' else 100 if resolution == 'medium (100)' else 500

        self.gui = gui
        self.preview = None  # the preview window i will put my preview image in
        self.image = None  # the preview image; i need a reference to it to update it

        self.weights = []

        # if image does not exist, don't start thread
        try:
            Image.open(self.image_path)
        except (FileNotFoundError, PermissionError):
            self.gui.update_status("image file not found", err=True)
            return

        # if directory does not exist, don't start thread
        if not isdir(self.dest_dir_path):  # folder does not exist
            self.gui.update_status("destination folder not found", err=True)
            return

        # if file is in use, update status message and don't start thread
        if self.gui.file_locked(self.dest_dir_path + "\\" + self.result_file_name):
            self.gui.update_status("destination file already in use", err=True)
            return

        # start thread
        self.start()

    # build wright arrays from files/asciify/weights.txt
    def read_weights(self):
        # there are 256 possible values (0-255). prepare a spot on the list for each
        for i in range(256):
            self.weights.append("")

        with open('files/asciify/weights.txt', 'r') as f:
            lines = f.readlines()  # one line per weight, each line lists characters with that weight
            for line in lines:
                n, p = (int(line.split(": ")[0]), line.split(": ")[1])
                self.weights[n] = list(map(int, p.split(" ")))

    # pick a single character for each weight to keep palette consistent.
    # if this method is not called pixels with the same brightness may be different characters
    def limit_palette(self):
        for w in range(len(self.weights)):
            if len(self.weights[w]) > 1:
                self.weights[w] = [random.choice(self.weights[w])]

    def resize_image(self, image):
        w, h = image.size

        # the character images are 10*22 pixels; must stretch image so when converted the two stretches cancel out
        w = w * 22
        h = h * 10

        ratio = h / w
        if ratio > 0:  # height was > width
            w = self.resolution
            h = w * ratio
        else:
            h = self.resolution
            w = h / ratio

        image = image.resize((int(w), int(h)), resample=Image.LANCZOS)
        return image

    def find_lighter(self, intent):
        d = 0
        while intent + d <= 255 and len(self.weights[intent + d]) == 0:
            d += 1
        if intent + d > 255:
            return -1
        elif len(self.weights[intent + d]) != 0:
            return d

    def find_darker(self, intent):
        d = 0
        while intent - d >= 0 and len(self.weights[intent - d]) == 0:
            d += 1
        if intent - d < 0:
            return -1
        elif len(self.weights[intent - d]) != 0:
            return d

    # because not all weight values have characters i have to find the closest weight that does
    def get_true_weight(self, intent):
        true = 0

        if len(self.weights[intent]) > 0:
            true = intent
        else:
            light = self.find_lighter(intent)
            dark = self.find_darker(intent)

            if dark == -1:
                true = intent + light
            elif light == -1:
                true = intent - dark
            else:
                if light == dark:
                    true = random.choice([intent + light, intent - dark])
                elif light < dark:
                    true = intent + light
                elif dark < light:
                    true = intent - dark

        return true

    # convert a single image into a string of chars and return the result
    def asciify(self, image):
        unicode = ""

        # the first version of asciify was meant for viewing in dark mode (white text on black background)
        # by default lighter pixels become darker characters
        # must invert image to ensure values are correct when viewed in black characters on white background
        if not self.white_on_black:
            image = ImageChops.invert(image)

        image = self.resize_image(image)
        image = image.convert('L')  # black and white
        w, h = image.size
        for hi in range(h):
            for wi in range(w):
                weight = self.get_true_weight(image.getpixel((wi, hi)))
                unicode += chr(random.choice(self.weights[weight]))
            unicode += "\n"

        return unicode

    def config_preview(self):
        # create preview window tab
        self.preview = self.gui.new_tab(self.command, file=self.result_file_name, path=self.dest_dir_path)

        # create a label to hold a preview of the text
        self.image = ttk.Label(master=self.preview.container, text="loading preview")
        self.image.grid(row=0, column=0)

        # preview is the original image
        img = DynamicGUI.open_resized_image(self.image_path)
        self.image.configure(image=img)
        self.image.photo = img  # prevent the image from getting garbage collected

    def run(self):
        # mark file as in use
        self.gui.lock_file(self.dest_dir_path + "\\" + self.result_file_name)

        self.config_preview()

        # prepare character list
        self.read_weights()
        if self.static:
            self.limit_palette()

        image = Image.open(self.image_path).convert("RGB")
        text = self.asciify(image)

        # put text in preview (self.image is just a label)
        self.image.configure(image="", text=text)
        self.image.photo = None  # allow garbage collection of old image

        # save text in a txt file in destination folder
        with open(self.dest_dir_path + "\\" + self.result_file_name, 'w', encoding='utf-8') as f:
            f.write(text)

        # unmark file as in use
        self.gui.unlock_file(self.dest_dir_path + "\\" + self.result_file_name)

        # wait for a bit then remove this preview tab
        sleep(5)
        self.gui.remove_tab(self.preview.name)
