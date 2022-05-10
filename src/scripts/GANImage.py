import pickle
import threading
from enum import Enum
from os.path import isdir
from time import sleep
from tkinter import ttk
import PIL
import dnnlib
import dnnlib.tflib as tflib
from PIL import Image
from torchvision import transforms
import numpy as np

from src.DynamicGUI import DynamicGUI

path = "res/gan/models/"


class Datasets(Enum):
    CATS = "cats"
    FLOWERS = "flowers"
    POKEMON = "pokemon"
    ANIME = "anime"
    MICROSCOPE = "microscope"
    TEXTURES = "textures"
    ABSTRACT1 = "abstract art 1"
    ABSTRACT2 = "abstract art 2"
    FIGURE = "figure drawings"
    MODEL = "model.ckpt-533504"
    NETWORK = "network-snapshot-026392"


class GANImage(threading.Thread):

    def __init__(self, gui, dataset, output_dir_path, type, input_path=None):
        super().__init__(daemon=True)

        self.gui = gui
        self.dataset = dataset
        self.output_dir_path = output_dir_path
        self.input_path = input_path

        # if directory does not exist, don't start thread
        if not isdir(output_dir_path):  # folder does not exist
            self.gui.update_status("destination folder not found", err=True)
            return

        # check for valid input image, generate if none given
        if input_path:
            try:
                image = Image.open(input_path)
            except (FileNotFoundError, PermissionError):
                self.gui.update_status("image file not found", err=True)
                return

        self.command = "GAN image"
        self.preview = None
        self.preview_image = None
        self.image_name = ""

        # get unused file path
        self.output_path = self.get_output_path(output_dir_path)

        # start thread
        self.start()

    def get_output_path(self, output_dir_path):
        new_path = ""
        valid = False
        index = 0
        while not valid:
            self.image_name = self.dataset + "_" + str(index) + ".png"
            new_path = output_dir_path + "\\" + self.image_name
            index += 1
            # assume valid
            valid = True

            # file already exists, path not valid
            try:
                Image.open(new_path)
                valid = False
            except FileNotFoundError:
                pass

            # file is in use, path not valid
            if self.gui.file_locked(new_path):
                valid = False

        return new_path

    @staticmethod
    def inputify_image(image, size):
        # resize
        image.resize(size)

        # make grayscale
        # image = ImageOps.grayscale(image)

        # transform pil image to pytorch tensor
        transform = transforms.Compose([transforms.PILToTensor()])
        tensor = transform(image)

        # limit values to [0, 1)
        for i in image:
            for j in image[i]:
                image[i][j] /= 256

        return tensor

    def generate_output_image(self):
        # create tensorflow session in preparation for unpickling model
        self.preview.progress(0)
        self.preview.update("starting tensorflow session...")
        try:
            dnnlib.tflib.init_tf()
        except AssertionError:
            pass
        self.preview.progress(15)

        # load model
        self.preview.update("loading model...")
        file = open(path + self.dataset + ".pkl", 'rb')
        G, D, Gs = pickle.load(file, encoding='latin1')
        Gs_kwargs = dnnlib.EasyDict()
        Gs_kwargs.output_transform = dict(func=tflib.convert_images_to_uint8, nchw_to_nhwc=True)
        Gs_kwargs.randomize_noise = False
        rnd = np.random.RandomState()
        noise_vars = [var for name, var in Gs.components.synthesis.vars.items() if name.startswith('noise')]
        tflib.set_vars({var: rnd.randn(*var.shape.as_list()) for var in noise_vars})  # [height, width]
        self.preview.progress(30)

        # get input

        input_image = None
        if self.input_path:
            self.preview.update("preprocessing input...")
            input_image = self.inputify_image(self.input_path, *Gs.input_shape[1:])
        else:
            self.preview.update("generating input...")
            input_image = rnd.randn(1, *Gs.input_shape[1:])  # [minibatch, component]
        self.preview.progress(50)

        self.preview.update("generating image...")
        # pass input image through model
        output = Gs.run(input_image, None, **Gs_kwargs)  # [minibatch, height, width, channel]
        # get image from output
        output_image = PIL.Image.fromarray(output[0], 'RGB')
        self.preview.progress(90)

        # put image in preview
        img = DynamicGUI.resize(output_image)
        self.preview_image.configure(image=img)
        self.preview_image.image = img  # prevent garbage collection

        # save image to output file
        self.preview.update("saving image...")
        output_image.save(self.output_path)
        self.preview.progress(100)

        self.preview.update("done.")

    def config_preview(self):
        self.preview = self.gui.new_tab(self.command, file=self.image_name, path=self.output_dir_path)
        # create a label to hold an image preview of the selected file
        self.preview_image = ttk.Label(master=self.preview.container, text="generating image...")
        self.preview_image.grid(row=0, column=0)

    def run(self):
        # mark file as in use
        self.gui.lock_file(self.output_path)

        self.config_preview()

        self.generate_output_image()

        # unmark file as in use
        self.gui.unlock_file(self.output_path)

        # wait for a bit before making preview tab disappear
        sleep(5)
        self.gui.remove_tab(self.preview.name)
