from os.path import exists
import threading
from os.path import isdir
from time import sleep
from tkinter import ttk
import random
import cv2
from cv2 import VideoCapture, VideoWriter, VideoWriter_fourcc
from src.DynamicGUI import DynamicGUI
from PIL import Image, ImageChops, ImageDraw, ImageFont
import ffmpeg
from numpy import array

W, H = (11, 18)  # width and height of one character
font = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 18, encoding='utf-8')

working_folder_path = "files\\working_folder"  # temporarily store video


# transforms image into image of characters
class Ascheatfier(threading.Thread):
    def __init__(self, gui, image_path, dest_dir_path, resolution, static, white_on_black):
        super().__init__(daemon=True)

        self.command = "Ascheatfy"  # will appear in the preview window tab

        # if path was given with slashes, convert to backslash path
        self.image_path = image_path.replace('/', '\\')  # the image to be transformed
        self.dest_dir_path = dest_dir_path.replace('/', '\\')  # the path to the folder where the mp3 should be placed
        if self.dest_dir_path[len(self.dest_dir_path) - 1] == '\\':  # if last character is a backslash
            self.dest_dir_path = self.dest_dir_path[:-1]  # remove last backslash character

        # get the name of the image from the path
        self.image_name = self.image_path.split("\\").pop()  # split into path parts, get last part (filename)
        self.image_name = self.image_name.split(".")[0]  # remove file extension

        self.extension = self.image_path.split("\\").pop().split(".").pop()  # the source file extension
        self.result_file_name = self.image_name + " - ascheatfied." + self.extension  # the destination file name + extension

        self.static = static
        self.white_on_black = white_on_black
        self.resolution = 50 if resolution == 'small (50)' else 150 if resolution == 'medium (150)' else 300

        self.gui = gui
        self.preview = None  # the preview window i will put my preview image in
        self.image = None  # the preview image; i need a reference to it to update it

        self.char_images = {}

        # if image/video does not exist, don't start thread
        if not exists(self.image_path):
            self.gui.update_status("image/video file not found", err=True)
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

    # build weights, an array of arrays, from files/ascheatfy/weights.txt
    def read_weights(self):
        weights = []

        # there are 256 possible values (0-255). prepare a spot on the list for each
        for i in range(256):
            weights.append("")

        with open('files/ascheatfy/weights.txt', 'r') as f:
            lines = f.readlines()  # one line per weight, each line lists characters with that weight
            for line in lines:
                n, p = (int(line.split(": ")[0]), line.split(": ")[1])
                weights[n] = list(map(int, p.split(" ")))

        if self.static:
            weights = self.limit_palette(weights)

        return weights

    # pick a single character for each weight to keep palette consistent.
    # if this method is not called pixels with the same brightness may be different characters
    def limit_palette(self, weights):
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
            self.update_preview(result)

        # the first version of asciify was meant for viewing in dark mode (white text on black background)
        # by default lighter pixels become darker characters
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
                self.update_preview(result)
                self.preview.progress(100 * hi / h)

        return result

    # have to convert a video. convert each frame as if it were an image
    # https://gist.github.com/SebOh/5d2438c7987591757a3591495720a5e7
    def asciify_mp4(self):
        video = VideoCapture(self.image_path)
        result = VideoWriter(working_folder_path + "\\video.mp4",
                             VideoWriter_fourcc('m', 'p', '4', 'v'), video.get(cv2.CAP_PROP_FPS),
                             self.get_resized_size((int(video.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                                   int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))))
        frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

        self.preview.update("ascheatfying")
        index = 0
        while video.isOpened():
            ret, cv2_im = video.read()  # i think ret is short for retrieved; boolean, false when no more frames
            if ret:
                frame_image = Image.fromarray(cv2.cvtColor(cv2_im, cv2.COLOR_BGR2RGB))  # convert from nparray to pil image

                asciified = self.asciify(frame_image.convert("RGB"), silent=True)  # tell method not to update preview

                frame_array = cv2.cvtColor(array(asciified), cv2.COLOR_RGB2BGR)  # convert back from pil image to nparray
                result.write(frame_array)  # write method takes numpy array as parameter
                self.update_preview(asciified)
                self.preview.progress(index * 100 / frame_count)

                index += 1

            elif not ret:
                break

        video.release()
        result.release()

        # add the audio
        self.preview.update("adding audio")
        audio = ffmpeg.input(self.image_path).audio
        video = ffmpeg.input(working_folder_path+"\\video.mp4").video
        ffmpeg.output(audio, video, self.dest_dir_path+"\\"+self.result_file_name)\
            .overwrite_output()\
            .run(quiet=True)

        self.preview.progress(100)
        self.preview.update("asciified video")

    # have to convert a gif. convert each frame as if it were an image
    # https://stackoverflow.com/questions/7503567/python-how-i-can-get-gif-frames
    # https://stackoverflow.com/questions/53364769/get-frames-per-second-of-a-gif-in-python#53365469
    def asciify_gif(self):
        self.preview.update("preparing")

        # must loop once to find total number of frames for updating the progress bar. also get durations while at it
        frame = Image.open(self.image_path)
        durations = []
        frame_count = 0
        try:
            while 1:
                durations.append(frame.info['duration'])
                frame_count += 1
                frame.seek(frame.tell() + 1)
        except EOFError:
            pass  # do nothing

        self.preview.update("ascheatfying")
        result_frames = []
        frame = Image.open(self.image_path)
        try:
            while 1:
                asciified = self.asciify(frame.convert("RGB"), silent=True)  # tell method not to update preview
                result_frames.append(asciified)
                self.update_preview(asciified)
                self.preview.progress(frame.tell() * 100 / frame_count)
                frame.seek(frame.tell() + 1)
        except EOFError:
            self.preview.update("saving gif")
            result_frames[0].save(self.dest_dir_path + "\\" + self.result_file_name, format='GIF',
                                  append_images=result_frames[1:], save_all=True, duration=durations, loop=0)

        self.preview.update("ascheatfied gif")
        self.preview.progress(100)

    # ascheatfy a single image
    def asciify_image(self):
        # preview is the original image
        img = DynamicGUI.open_resized_image(self.image_path)
        self.image.configure(image=img)
        self.image.photo = img  # prevent the image from getting garbage collected

        image = Image.open(self.image_path).convert("RGB")

        self.preview.update("ascheatfying")
        result = self.asciify(image)

        self.preview.update("saving image")
        # save image in a png file in destination folder
        result.save(fp=self.dest_dir_path + "\\" + self.result_file_name)

        self.preview.update("ascheatfied image.")
        self.preview.progress(100)

    def config_preview(self):
        self.preview = self.gui.new_tab(self.command, file=self.result_file_name, path=self.dest_dir_path)
        # create a label to hold an image preview of the frames as they are converted (if video / gif)
        self.image = ttk.Label(master=self.preview.container, text="loading preview")
        self.image.grid(row=0, column=0)

    def update_preview(self, image):
        img = DynamicGUI.resize(image)
        self.image.configure(image=img)
        self.image.photo = img  # prevent the image from getting garbage collected

    def run(self):

        # mark file as in use
        self.gui.lock_file(self.dest_dir_path + "\\" + self.result_file_name)

        self.config_preview()

        # prepare character images
        self.generate_character_images()

        if self.extension == "mp4":
            self.asciify_mp4()
        elif self.extension == "gif":
            self.asciify_gif()
        else:  # have to convert an image. convert it
            self.asciify_image()

        # unmark file as in use
        self.gui.unlock_file(self.dest_dir_path + "\\" + self.result_file_name)

        # wait for a bit then remove this preview tab
        sleep(5)
        self.gui.remove_tab(self.preview.name)