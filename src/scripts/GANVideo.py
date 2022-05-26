import pickle
import random

import PIL
import cv2
import dnnlib
import dnnlib.tflib as tflib
from PIL import Image
from cv2 import VideoWriter, VideoWriter_fourcc
from numpy import array
from torchvision import transforms
import numpy as np
import shutil

from src.File import File
from src.Script import Script, OptionList
from src.globals import Globals

models_path = "res/gan/models/"
fps = 30

Speeds = OptionList({
    "slow": 1,
    "medium": 3,
    "fast": 6
})


Datasets = OptionList({
    "cats": "cats",
    "flowers": "flowers",
    "pokemon": "pokemon",
    "anime": "anime",
    "microscope": "microscope",
    "textures": "textures",
    "abstract art 1": "abstract art 1",
    "abstract art 2": "abstract art 2",
    "figure drawings": "figure drawings",
    "model.ckpt-533504": "model.ckpt-533504",
    "network-snapshot-026392": "network-snapshot-026392"
})

TransitionTypes = OptionList({
    "random": 0,
    "sequences": 1,
    "constant": 2,
    "move right": 3,
    "zoom": 4
})


class Model:
    def __init__(self, path):
        self.shape = (0, 0)
        self.path = path

    def get_size(self):
        return self.shape

    def load(self):
        with open(self.path, 'rb') as file:
            G, D, Gs = pickle.load(file, encoding='latin1')

        Gs_kwargs = dnnlib.EasyDict()
        Gs_kwargs.output_transform = dict(func=tflib.convert_images_to_uint8, nchw_to_nhwc=True)
        Gs_kwargs.randomize_noise = False
        rnd = np.random.RandomState()
        noise_vars = [var for name, var in Gs.components.synthesis.vars.items() if name.startswith('noise')]
        tflib.set_vars({var: rnd.randn(*var.shape.as_list()) for var in noise_vars})  # [height, width]


class GANVideo(Script):

    def __init__(self, dataset, input_path, output_path, speed, duration, transition_type):
        super().__init__(output_path=output_path)

        self.dataset = Datasets.get_option_value(dataset)
        self.speed = Speeds.get_option_value(speed)
        self.transition_type = TransitionTypes.get_option_value(transition_type)
        self.duration = duration

        self._script_name = "GAN"
        self._input_types = File.Types.MP4
        self._output_type = File.Types.MP4

        self.model = None
        self.inputs = []

        # start thread
        self.start()

    def validate_arguments(self):
        # ensure duration is numerical
        try:
            self.duration = float(self.duration)
        except ValueError:
            Globals.gui.status("duration must be numerical", err=True)
            raise ValueError

        # duration must be > 0
        # duration must be less than or equal to 10 minutes (for now)
        if self.duration <= 0:
            Globals.gui.status("duration cannot be 0", err=True)
            raise ValueError
        elif self.duration > 5:
            Globals.gui.status("duration must be under 5 minutes", err=True)
            raise ValueError

    def generate_input(self):
        # generate number of frames in this sequence
        frames = int(fps / self.speed)  # how many frames to generate is determined by speed

        # amount to increase or decrease by is determined by speed
        delta = self.speed / 1000000000000000  # 1 / this number is the smallest possible value in python

        if self.transition_type == TransitionTypes.get_option_value("random"):
            for i in range(frames):
                # loop over all "pixels" and either increase or decrease by delta
                self.inputs.append("")
        elif self.transition_type == TransitionTypes.get_option_value("sequences"):
            original = self.inputs[len(self.inputs) - 1]
            new = ""  # generate random input
            # transition smoothly from original to new
            for i in range(frames):
                # increase each pixel by the initial difference divided by the number of frames
                self.inputs.append("")
        elif self.transition_type == TransitionTypes.get_option_value("constant"):
            pass

        input_image = rnd.randn(1, *Gs.input_shape[1:])  # [minibatch, component]

    def generate_frame(self):
        # pass input image through model
        output = Gs.run(input_image, None, **Gs_kwargs)  # [minibatch, height, width, channel]
        # get image from output
        output_image = PIL.Image.fromarray(output[0], 'RGB')
        return output_image

    def convert(self):
        # create tensorflow session in preparation for unpickling model
        self.preview.progress_update("starting tensorflow session...")
        session = dnnlib.tflib.init_tf()
        self.preview.progress_amount(5)

        # load model
        self.preview.progress_update("loading model...")
        self.model = Model(models_path + self.dataset + ".pkl")
        self.model.load()
        self.preview.progress_amount(10)

        # prepare output
        result = VideoWriter(Globals.working_folder_path + "\\video.mp4",
                             VideoWriter_fourcc('m', 'p', '4', 'v'), fps, self.model.get_size())

        # keep generating until we reach desired length
        frames = 0
        frames_goal = self.duration * 60 * fps   # duration is given in minutes
        while frames < frames_goal:
            if len(self.inputs) <= 2:
                # generate batch of input
                self.preview.progress_update("generating input...")
                self.generate_input()
                self.preview.progress_update("generating frames...")

            frame = self.generate_frame()
            self.inputs.pop(0)  # remove first index

            # write frame to output
            frame_array = cv2.cvtColor(array(frame), cv2.COLOR_RGB2BGR)
            result.write(frame_array)  # write method takes numpy array as parameter

            # update preview once every 5 frames
            if frames % 5 == 0:
                self.preview.progress_amount(10 + 85 * frames / frames_goal)
                self.preview.put_image(frame)

            frames += 1

        # copy temporary file to destination folder
        self.preview.progress_update("saving image...")
        shutil.copyfile(Globals.working_folder_path + "\\video.mp4", self.output_file.get_full_path())
        self.preview.progress_amount(100)

        session.close()
        self.preview.progress_update("done.")
