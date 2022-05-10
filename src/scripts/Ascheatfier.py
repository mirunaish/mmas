from enum import Enum
import random
import cv2
from cv2 import VideoCapture, VideoWriter, VideoWriter_fourcc
from PIL import Image, ImageChops, ImageDraw, ImageFont
import ffmpeg
from numpy import array

from src.File import File
from src.Script import Script

W, H = (11, 18)  # width and height of one character
font = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 18, encoding='utf-8')

working_folder_path = "res\\working_folder"  # temporarily store video


class Resolution(Enum):
    SMALL = 50
    MEDIUM = 100
    BIG = 500


# transforms image into image of characters
class Ascheatfier(Script):
    def __init__(self, gui, input_path, output_path, resolution, static, white_on_black):
        super().__init__(gui, input_path, output_path)

        self._script_name = "Ascheatfy"
        self._input_types = [File.Types.PNG, File.Types.MP4]  # allowed input types
        self._output_type = File.Types.MATCH_INPUT  # output type. if "MATCH_INPUT", is the same as input type

        self.static = static
        self.white_on_black = white_on_black
        self.resolution = resolution

        self.char_images = {}

        self.start()

    # build weights, an array of arrays, from res/ascheatfy/weights.txt
    def read_weights(self):
        weights = []

        # there are 256 possible values (0-255). prepare a spot on the list for each
        for i in range(256):
            weights.append("")

        with open('res/ascheatfy/weights.txt', 'r') as f:
            lines = f.readlines()  # one line per weight, each line lists characters with that weight
            for line in lines:
                n, p = (int(line.split(": ")[0]), line.split(": ")[1])
                weights[n] = list(map(int, p.split(" ")))

        if self.static:
            weights = self.limit_palette(weights)

        return weights

    # pick a single character for each weight to keep palette consistent.
    # if this method is not called pixels with the same brightness may be different characters
    @staticmethod
    def limit_palette(weights):
        for w in range(len(weights)):
            if len(weights[w]) > 1:
                weights[w] = [random.choice(weights[w])]
        return weights

    # i probably copy-pasted some of this function from stackoverflow
    # generate the ascheatfied image
    def generate_image(self, character):
        img = Image.new("RGBA", (W, H), (0, 0, 0) if self.white_on_black else (255, 255, 255))
        draw = ImageDraw.Draw(img)
        offset_w, offset_h = font.getoffset(chr(character))
        w, h = draw.textsize(str(chr(character)), font=font)
        pos = ((W - w - offset_w) / 2, (H - h - offset_h) / 2)
        draw.text(pos, chr(character), "white" if self.white_on_black else "black", font=font)  # draw the character
        return img

    # generate an image of each character and save in self.char_images
    def generate_character_images(self):
        weights = self.read_weights()
        for w in range(256):  # for each weight value
            self.char_images.update({w: {}})
            for c in weights[w]:  # for each character that has this weight
                self.char_images.get(w).update({c: self.generate_image(c)})

    # return the size a resized image would be; for asciify_mp4 method
    def get_resized_size(self, size):
        w, h = size

        w = w * H
        h = h * W

        ratio = h / w
        if ratio > 0:  # height was > width
            w = self.resolution
            h = w * ratio
        else:
            h = self.resolution
            w = h / ratio

        return int(w)*W, int(h)*H

    # resize the image so that each pixel maps to one character
    def resize_image(self, image):
        w, h = image.size

        # the character images are W*H pixels; must stretch image so when converted the two stretches cancel out
        w = w * H
        h = h * W

        ratio = h / w
        if ratio > 0:  # height was > width
            w = self.resolution
            h = w * ratio
        else:
            h = self.resolution
            w = h / ratio

        image = image.resize((int(w), int(h)), resample=Image.LANCZOS)
        return image

    # find the first weight that contains characters lighter than intent
    def find_lighter(self, intent):
        d = 0
        while intent + d <= 255 and len(self.char_images.get(intent + d).values()) == 0:
            d += 1
        if intent + d > 255:
            return -1
        elif len(self.char_images.get(intent + d).values()) != 0:
            return d

    # find the first weight that contains characters darker than intent
    def find_darker(self, intent):
        d = 0
        while intent - d >= 0 and len(self.char_images.get(intent - d).values()) == 0:
            d += 1
        if intent - d < 0:
            return -1
        elif len(self.char_images.get(intent - d).values()) != 0:
            return d

    # because not all weight values have characters, i have to find the closest weight that does
    def get_true_weight(self, intent):
        true = 0

        if len(self.char_images.get(intent).values()) > 0:
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

    # convert a single image into an ascheatfied image and return the result
    def asciify(self, image, silent=False):
        image = self.resize_image(image)

        # create result image; W*H px rectangle for each pixel in source image
        w, h = image.size
        result = Image.new("RGBA", (w * W, h * H), "black" if self.white_on_black else "white")
        if not silent:
            self.preview.put_image(result)

        # the first version of asciify was meant for viewing in dark mode (white text on black background)
        # by default lighter pixels become denser characters
        # must invert image to ensure values are correct when viewed in black characters on white background
        if not self.white_on_black:
            image = ImageChops.invert(image)

        image = image.convert('L')  # black and white

        # loop over pixels in source image
        for hi in range(h):
            for wi in range(w):
                weight = self.get_true_weight(image.getpixel((wi, hi)))
                char_img = self.char_images.get(weight).get(random.choice(list(self.char_images.get(weight).keys())))
                result.alpha_composite(char_img, dest=(wi * W, hi * H))
            if not silent:
                self.preview.put_image(result)
                self.preview.progress_amount(90 * hi / h)

        return result

    # have to convert a video. convert each frame as if it were an image
    def convert_mp4(self):
        self.preview.progress_update("processing video...")
        video = VideoCapture(self.input_file.get_full_path())
        result = VideoWriter(working_folder_path + "\\video.mp4",
                             VideoWriter_fourcc('m', 'p', '4', 'v'), video.get(cv2.CAP_PROP_FPS),
                             self.get_resized_size((int(video.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                                   int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))))
        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.preview.progress_amount(10)

        self.preview.progress_update("ascheatfying...")
        index = 0
        while video.isOpened():
            ret, cv2_im = video.read()  # i think ret is short for retrieved; boolean, false when no more frames
            if ret:
                # convert from numpy array to pillow image
                frame_image = Image.fromarray(cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB))

                asciified = self.asciify(frame_image.convert("RGB"), silent=True)  # tell method not to update preview
                self.preview.put_image(asciified)

                # convert back from pillow image to numpy array
                frame_array = cv2.cvtColor(array(asciified), cv2.COLOR_RGB2BGR)
                result.write(frame_array)  # write method takes numpy array as parameter
                self.preview.progress_amount(10 + index * 80 / frame_count)

                index += 1

            elif not ret:
                break

        video.release()
        result.release()

        # add the audio
        self.preview.progress_update("processing audio...")
        audio = ffmpeg.input(self.input_file.get_full_path()).audio
        video = ffmpeg.input(working_folder_path+"\\video.mp4").video
        ffmpeg.output(audio, video, self.output_file.get_full_path())\
            .overwrite_output()\
            .run(quiet=True)

    # have to convert a gif. convert each frame as if it were an image
    def convert_gif(self):
        # must loop once to find total number of frames for updating the progress bar. also get durations while at it
        self.preview.progress_update("processing gif...")
        frame = Image.open(self.input_file.get_full_path())
        durations = []
        frame_count = 0
        try:
            while 1:
                durations.append(frame.info['duration'])
                frame_count += 1
                frame.seek(frame.tell() + 1)
        except EOFError:
            pass  # do nothing
        self.preview.progress_amount(10)

        self.preview.progress_update("ascheatfying...")
        result_frames = []
        frame = Image.open(self.input_file.get_full_path())
        try:
            while 1:
                asciified = self.asciify(frame.convert("RGB"), silent=True)  # tell method not to update preview
                result_frames.append(asciified)
                self.preview.put_image(asciified)
                self.preview.progress_amount(10 + frame.tell() * 80 / frame_count)
                frame.seek(frame.tell() + 1)
        except EOFError:
            pass  # eof, do nothing

        self.preview.progress_update("saving gif...")
        result_frames[0].save(self.output_file.get_full_path(), format='GIF', append_images=result_frames[1:],
                              save_all=True, duration=durations, loop=0)

    # ascheatfy a single image
    def convert_image(self):
        # preview is the original image
        self.preview.put_image(self.input_file.get_full_path())

        image = Image.open(self.input_file.get_full_path()).convert("RGB")

        self.preview.progress_update("ascheatfying...")
        result = self.asciify(image)
        self.preview.progress_amount(90)

        self.preview.progress_update("saving image")
        # save image in a png file in destination folder
        result.save(fp=self.output_file.get_full_path())

    def convert(self):
        # prepare character images
        self.generate_character_images()

        self.preview.progress_amount(0)
        self.preview.progress_update("loading...")

        if self.input_file.extension == File.Types.MP4:
            self.convert_mp4()
        elif self.input_file.extension == File.Types.GIF:
            self.convert_gif()
        elif self.input_file.extension == File.Types.PNG:  # have to convert an image. convert it
            self.convert_image()

        self.preview.progress_update("ascheatfied.")
        self.preview.progress_amount(100)
