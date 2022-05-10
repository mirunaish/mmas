import threading
from os.path import isdir
from tkinter import ttk
from math import sqrt
from PIL import Image
from pydub import AudioSegment
import tomita.legacy.pysynth as synth
from time import sleep

from src.DynamicGUI import DynamicGUI

working_folder_path = "files/working_folder"  # folder where some temporary things will be stored


class ImageToMP3(threading.Thread):

    def __init__(self, gui, image_path, dest_dir_path):
        super().__init__(daemon=True)  # will continue to run even if main window is closed

        self.command = "Image to MP3"  # will appear in the preview window tab

        # if path was given with slashes, convert to backslash path
        self.image_path = image_path.replace('/', '\\')   # the image to be transformed
        self.dest_dir_path = dest_dir_path.replace('/', '\\')  # the path to the folder where the mp3 should be placed
        if self.dest_dir_path[len(self.dest_dir_path) - 1] == '\\':  # if last character is a backslash
            self.dest_dir_path = self.dest_dir_path[:-1]  # remove last backslash character

        # get the name of the image from the path
        self.image_name = self.image_path.split("\\").pop()  # split into path parts, get last part (filename)
        self.image_name = self.image_name.split(".")[0]  # remove file extension

        self.gui = gui
        self.preview = None  # the preview window i will put my preview image in

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
        if self.gui.file_locked(self.dest_dir_path + "\\" + self.image_name + ".mp3"):
            self.gui.update_status("destination file already in use", err=True)
            return

        # start thread
        self.start()

    # makes the image smaller (from its size to max 25x25)
    def smallify(self, image):
        x, y = image.size
        if x * y > 25 * 25:  # image is too big
            area = x * y
            div = sqrt(area / 625)  # what each side should be divided by
            new_x = max(int(x / div), 1)  # dimensions have to be at least 1
            new_y = max(int(y / div), 1)
            image = image.resize((new_x, new_y), resample=Image.LANCZOS)  # a slow but good resizing algorithm
        image.save(working_folder_path + "/smallified.png")
        return image

    # converts the image to a tuple of note codes
    def convert_to_notes(self, image):
        note_sequence = []
        for i in range(3):  # one for each color channel (r, g, b)
            note_sequence.append([('r', 4)])  # each channel begins with a rest
        notes = [
            "a0", "a#0", "b0", "c1", "c#1", "d1", "d#1", "e1", "f1", "f#1", "g1", "g#1", "a1", "a#1", "b1", "c2", "c#2",
            "d2", "d#2", "e2", "f2", "f#2", "g2", "g#2", "a2", "a#2", "b2", "c3", "c#3", "d3", "d#3", "e3", "f3", "f#3",
            "g3", "g#3", "a3", "a#3", "b3", "c4", "c#4", "d4", "d#4", "e4", "f4", "f#4", "g4", "g#4", "a4", "a#4", "b4",
            "c5", "c#5", "d5", "d#5", "e5", "f5", "f#5", "g5", "g#5", "a5", "a#5", "b5", "c6", "c#6", "d6", "d#6", "e6",
            "f6", "f#6", "g6", "g#6", "a6", "a#6", "b6", "c7", "c#7", "d7", "d#7", "e7", "f7", "f#7", "g7", "g#7", "a7",
            "a#7", "b7", "c8"]
        # ^ for easy converting from rgb value to note

        pixel_map = image.load()  # image pixel data
        x, y = image.size

        for i in range(y):
            for j in range(x):
                r, g, b = pixel_map[j, i]  # get r g b values of current pixel
                red_pitch = r % 88
                red_length = (r / 88 + 1) * 2  # number magic
                note_sequence[0].append((str(notes[red_pitch]), int(red_length)))  # red note
                green_pitch = g % 88
                green_length = (g / 88 + 1) * 2
                note_sequence[1].append((str(notes[green_pitch]), int(green_length)))  # green note
                blue_pitch = b % 88
                blue_length = (b / 88 + 1) * 2
                note_sequence[2].append((str(notes[blue_pitch]), int(blue_length)))  # blue note

            # this doesn't have much practical effect in this new conversion
            for k in range(3):  # one for each color channel (r, g, b)
                note_sequence[k].append(('r', 4))  # a rest at the end of each line

        for i in range(3):  # one for each color channel (r, g, b)
            note_sequence[i] = tuple(note_sequence[i])  # turn the list into a tuple (that's what synth's function uses)

        return note_sequence

    def notes_to_wav(self, notes_sequence):
        synth.make_wav(notes_sequence[0], fn=working_folder_path + "/temp.wav", silent=True)  # create wav
        red = AudioSegment.from_file(working_folder_path + "/temp.wav")  # open wav with AudioSegment
        yield 1  # finished first channel
        synth.make_wav(notes_sequence[1], fn=working_folder_path + "/temp.wav", silent=True)
        green = AudioSegment.from_file(working_folder_path + "/temp.wav")
        yield 2  # second channel
        synth.make_wav(notes_sequence[2], fn=working_folder_path + "/temp.wav", silent=True)
        blue = AudioSegment.from_file(working_folder_path + "/temp.wav")
        yield 3  # third

        combined = red.overlay(green)
        combined = combined.overlay(blue)

        combined.export(working_folder_path + "/temp.wav", format='wav')

    # converts the wav to mp3
    def wav_to_mp3(self, mp3_name, folder_path):
        audio = AudioSegment.from_wav(working_folder_path + "\\temp.wav")
        audio.export(folder_path + "\\" + mp3_name + ".mp3", format="mp3")  # the one-liner was too long

    def convert(self):
        image = Image.open(self.image_path).convert("RGB")

        # make image smaller
        self.preview.update("preparing image")
        image = self.smallify(image)
        self.preview.progress(10)

        # convert image to notes
        self.preview.update("converting to notes")
        notes_sequence = self.convert_to_notes(image)
        self.preview.progress(25)

        # build wav file (that's the only format synth knows to create (at the time of making this - 2019))
        self.preview.update("building sounds")
        for i in self.notes_to_wav(notes_sequence):  # creates wav file in working folder, yields progress
            self.preview.progress(25 + i * 20)

        # convert wav to mp3
        self.preview.update("exporting " + self.image_name + ".mp3")
        self.wav_to_mp3(self.image_name, self.dest_dir_path)
        self.preview.progress(100)

        self.preview.update("converted image to music")

    def config_preview(self):
        self.preview = self.gui.new_tab(self.command, file=self.image_name + ".mp3", path=self.dest_dir_path)
        # create a label to hold an image preview of the selected file
        img = DynamicGUI.open_resized_image(self.image_path)
        w = ttk.Label(master=self.preview.container, image=img)
        w.photo = img  # prevent the image from getting garbage collected
        w.grid(row=0, column=0)

    def run(self):
        # mark file as in use
        self.gui.lock_file(self.dest_dir_path + "\\" + self.image_name + ".mp3")

        self.config_preview()

        self.convert()

        # unmark file as in use
        self.gui.unlock_file(self.dest_dir_path + "\\" + self.image_name + ".mp3")

        # wait for a bit before making preview tab disappear
        sleep(5)
        self.gui.remove_tab(self.preview.name)

