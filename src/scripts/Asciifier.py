import random
from enum import Enum

from PIL import Image, ImageChops

from src.File import File
from src.Script import Script


class Resolution(Enum):
    SMALL = 50
    MEDIUM = 100
    BIG = 500


# given an image turn it into a string
class Asciifier(Script):
    def __init__(self, gui, input_path, output_path, resolution, static, white_on_black):
        super().__init__(gui, input_path, output_path)

        self._script_name = "Asciify"
        self._input_types = [File.Types.PNG]
        self._output_type = File.Types.TXT

        self.static = static
        self.white_on_black = white_on_black
        self.resolution = resolution

        self.weights = []

        self.start()

    # build wright arrays from res/asciify/weights.txt
    def read_weights(self):
        # there are 256 possible values (0-255). prepare a spot on the list for each
        for i in range(256):
            self.weights.append("")

        with open('res/asciify/weights.txt', 'r') as f:
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

    def convert(self):
        self.preview.put_image(self.input_file.get_full_path())
        self.preview.progress_amount(0)

        self.preview.progress_update("preparing weights...")
        # prepare character list
        self.read_weights()
        if self.static:
            self.limit_palette()
        self.preview.progress_amount(10)

        image = Image.open(self.input_file.get_full_path()).convert("RGB")

        self.preview.progress_update("asciifying image...")
        text = self.asciify(image)
        self.preview.progress_amount(90)

        # put text in preview
        self.preview.put_text(text)

        self.preview.progress_update("saving...")
        # save text in a txt file in destination folder
        with open(self.output_file.get_full_path(), 'w', encoding='utf-8') as f:
            f.write(text)
        self.preview.progress_amount(100)
        self.preview.progress_update("asciified image.")
