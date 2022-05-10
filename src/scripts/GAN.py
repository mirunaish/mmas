import pickle
from enum import Enum
import PIL
import dnnlib
import dnnlib.tflib as tflib
from PIL import Image
from torchvision import transforms
import numpy as np

from src.File import File
from src.Script import Script

models_path = "res/gan/models/"


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


class GAN(Script):

    def __init__(self, gui, dataset, input_path, output_path):
        super().__init__(gui, input_path, output_path)

        self.dataset = dataset

        self._script_name = "GAN"
        self._input_types = [File.Types.PNG, File.Types.MP4, File.Types.GIF]
        self._output_type = File.Types.MATCH_INPUT

        # start thread
        self.start()

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

    def convert(self):
        # create tensorflow session in preparation for unpickling model
        self.preview.progress_amount(0)
        self.preview.progress_update("starting tensorflow session...")
        try:
            dnnlib.tflib.init_tf()
        except AssertionError:
            pass
        self.preview.progress_amount(10)

        # load model
        self.preview.progress_update("loading model...")
        file = open(models_path + self.dataset + ".pkl", 'rb')
        G, D, Gs = pickle.load(file, encoding='latin1')
        Gs_kwargs = dnnlib.EasyDict()
        Gs_kwargs.output_transform = dict(func=tflib.convert_images_to_uint8, nchw_to_nhwc=True)
        Gs_kwargs.randomize_noise = False
        rnd = np.random.RandomState()
        noise_vars = [var for name, var in Gs.components.synthesis.vars.items() if name.startswith('noise')]
        tflib.set_vars({var: rnd.randn(*var.shape.as_list()) for var in noise_vars})  # [height, width]
        self.preview.progress_amount(20)

        # get input
        if self.input_file is not None:
            self.preview.progress_update("preprocessing input...")
            input_image = self.inputify_image(self.input_file.get_full_path(), *Gs.input_shape[1:])
        else:
            self.preview.progress_update("generating input...")
            input_image = rnd.randn(1, *Gs.input_shape[1:])  # [minibatch, component]
        self.preview.progress_amount(30)

        self.preview.progress_update("generating image...")
        # pass input image through model
        output = Gs.run(input_image, None, **Gs_kwargs)  # [minibatch, height, width, channel]
        # get image from output
        output_image = PIL.Image.fromarray(output[0], 'RGB')
        self.preview.progress_amount(90)

        self.preview.put_image(output_image)

        # save image to output file
        self.preview.progress_update("saving image...")
        output_image.save(self.output_file.get_full_path())
        self.preview.progress_amount(100)

        self.preview.progress_update("done.")
