from math import sqrt
from PIL import Image
from pydub import AudioSegment
import tomita.legacy.pysynth as synth

from src.File import File
from src.Script import Script

working_folder_path = "res/working_folder"  # folder where some temporary things will be stored


class ImageToMP3(Script):

    def __init__(self, gui, input_path, output_path):
        super().__init__(gui, input_path, output_path)  # will continue to run even if main window is closed

        self._script_name = "ImageToMP3"
        self._input_types = [File.Types.PNG]
        self._output_type = File.Types.MP3

        self.start()

    # makes the image smaller (from its size to max 25x25)
    @staticmethod
    def smallify(image):
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
    @staticmethod
    def convert_to_notes(image):
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

    @staticmethod
    def notes_to_wav(notes_sequence):
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
    @staticmethod
    def wav_to_mp3(output_path):
        audio = AudioSegment.from_wav(working_folder_path + "\\temp.wav")
        audio.export(output_path, format="mp3")  # the one-liner was too long

    def convert(self):
        image = Image.open(self.input_file.get_full_path()).convert("RGB")

        # make image smaller
        self.preview.progress_update("preparing image")
        image = self.smallify(image)
        self.preview.progress_amount(10)

        # convert image to notes
        self.preview.progress_update("converting to notes")
        notes_sequence = self.convert_to_notes(image)
        self.preview.progress_amount(25)

        # build wav file (that's the only format synth knows to create)
        self.preview.progress_update("building sounds")
        for i in self.notes_to_wav(notes_sequence):  # creates wav file in working folder, yields progress
            self.preview.progress_amount(25 + i * 20)

        # convert wav to mp3
        self.preview.progress_update("exporting " + self.input_file.file_name + ".mp3")
        self.wav_to_mp3(self.output_file.get_full_path())
        self.preview.progress_amount(100)

        self.preview.progress_update("converted image to music")

