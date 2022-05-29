import pickle
import time
import PIL
import cv2
import dnnlib
import dnnlib.tflib as tflib
from PIL import Image
from cv2 import VideoWriter, VideoWriter_fourcc
from numpy import array
from numpy.random import RandomState
import shutil

from src.File import File
from src.Script import Script, OptionList
from src.globals import Globals

models_path = "res/gan/models/"
fps = 30

Speeds = OptionList({
    "slow": 1,
    "medium": 2,
    "fast": 4
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
    "imageNET": "model.ckpt-533504",
    "network-snapshot-026392": "network-snapshot-026392",
    "mystery": "ffhq"
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
        self.generator = None
        self.shape = (0, 0)
        self.path = path

        # set up some generation options
        self.args = dnnlib.EasyDict()
        self.args.output_transform = dict(func=tflib.convert_images_to_uint8, nchw_to_nhwc=True)
        self.args.randomize_noise = False

        self.random = RandomState(int(time.time()))

    def load(self):
        with open(self.path, 'rb') as file:
            generator, discriminator, generator_s = pickle.load(file, encoding='latin1')

        self.generator = generator
        self.shape = (1, *generator_s.input_shape[1:])

    def get_input_shape(self):
        return self.shape

    def get_output_size(self):
        # generate one image and get its size
        output = self.generate_frame(self.get_random_input())
        return output.size

    def get_random_input(self):
        return self.random.randn(*self.get_input_shape())

    def generate_frame(self, input_image):
        # pass input image through model
        output = self.generator.run(input_image, None, **self.args)
        # get image from output
        output_image = PIL.Image.fromarray(output[0], 'RGB')
        return output_image


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
            Globals.gui.update_status("duration must be numerical", err=True)
            raise ValueError

        # duration must be > 0
        # duration must be less than or equal to 10 minutes (for now)
        if self.duration <= 0:
            Globals.gui.update_status("duration cannot be 0", err=True)
            raise ValueError
        elif self.duration > 5:
            Globals.gui.update_status("duration must be under 5 minutes", err=True)
            raise ValueError

    def copy_last_input(self):
        return self.inputs[len(self.inputs) - 1].copy()

    def generate_input(self):
        # pick number of frames in this batch
        frames = int(fps / self.speed) * 10

        # amount to increase or decrease by is determined by speed
        delta = self.speed / 450

        # if the input is empty, generate an initial frame
        if not self.inputs:
            self.inputs.append(self.model.get_random_input())

        if self.transition_type == TransitionTypes.get_option_value("random"):
            for i in range(frames):
                new_input = self.copy_last_input()
                # loop over all "pixels" and either increase by delta, decrease by delta, or do nothing
                for j, pixel in enumerate(new_input):
                    choice = self.model.random.randint(0, 3)
                    if choice == 1:
                        new_input[j] = pixel + delta
                    elif choice == 2:
                        new_input[j] = pixel - delta
                self.inputs.append(new_input)

        elif self.transition_type == TransitionTypes.get_option_value("sequences"):
            original = self.inputs[len(self.inputs) - 1]
            goal = self.model.get_random_input()  # generate random input
            # transition smoothly from original to new
            for i in range(frames):
                new_input = self.copy_last_input()
                # increase each pixel by the initial difference divided by the number of frames
                for j, pixel in enumerate(new_input[0]):
                    new_input[0][j] += (goal[0][j] - original[0][j]) / frames
                self.inputs.append(new_input)

        elif self.transition_type == TransitionTypes.get_option_value("constant"):
            for i in range(frames):
                new_input = self.copy_last_input()
                # loop over all "pixels" and increase by delta
                for j, pixel in enumerate(new_input):
                    new_input[j] = pixel + delta
                self.inputs.append(new_input)

    def convert(self):
        # create tensorflow session in preparation for unpickling model
        self.preview.progress_update("starting tensorflow session...")
        try:
            session = dnnlib.tflib.init_tf()
        except AssertionError:
            # this happens every time the gan video is rerun without restarting the app
            print("caught you")
            pass
        self.preview.progress_amount(5)

        # load model
        self.preview.progress_update("loading model...")
        self.model = Model(models_path + self.dataset + ".pkl")
        self.model.load()
        self.preview.progress_amount(10)

        # prepare output
        result = VideoWriter(Globals.working_folder_path + "\\video.mp4",
                             VideoWriter_fourcc('m', 'p', '4', 'v'), fps, self.model.get_output_size())

        # keep generating until we reach desired length
        frames = 0
        frames_goal = self.duration * 60 * fps   # duration is given in minutes
        while frames < frames_goal:
            if len(self.inputs) <= 2:
                # generate batch of input
                self.preview.progress_update("generating input...")
                self.generate_input()
                self.preview.progress_update("generating frames...")

            frame = self.model.generate_frame(self.inputs.pop(0))  # remove first input

            # write frame to output
            frame_array = cv2.cvtColor(array(frame), cv2.COLOR_RGB2BGR)
            result.write(frame_array)  # write method takes numpy array as parameter

            # update preview once every 10 frames
            if frames % 10 == 0 or frames == frames_goal:
                self.preview.progress_amount(10 + 85 * frames / frames_goal)
                self.preview.put_image(frame)

            frames += 1

        result.release()

        # copy temporary file to destination folder
        self.preview.progress_update("saving image...")
        shutil.copyfile(Globals.working_folder_path + "\\video.mp4", self.output_file.get_full_path())
        self.preview.progress_amount(100)

        session.close()
        self.preview.progress_update("done.")
