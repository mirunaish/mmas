from enum import Enum
from tkinter import ttk
from tkinter import *
from src.DynamicGUI import DynamicGUI
from src.globals import Globals
from src.scripts.Ascheatfier import Ascheatfier, Resolution as AscheatResolution
from src.scripts.Asciifier import Asciifier, Resolution as AsciiResolution
from src.scripts.GANImage import Datasets as ImDatasets, GANImage
from src.scripts.GANVideo import Speed, Datasets as VidDatasets, GANVideo, TransitionTypes
from src.scripts.ImageToMP3 import ImageToMP3

# Handles the main, mostly static elements of the GUI: the side panel and the options panel
# The main GUI creates the dynamic GUI which contains the preview notebook and the status bar

root = Tk()

# configure root
root.geometry('800x450')
root.resizable(False, False)
root.title("Mozzarella's Multimedia Art Station")
icon = PhotoImage(file="./res/favicon.png")
root.iconphoto(True, icon)

# configure the panels
root.columnconfigure(0, weight=2, uniform="y")
root.columnconfigure(1, weight=0)
root.columnconfigure(2, weight=3, uniform="y")
root.columnconfigure(3, weight=0)
root.columnconfigure(4, weight=8, uniform="y")
root.rowconfigure(0, weight=1)
root.rowconfigure(1, weight=0)
root.rowconfigure(2, weight=0)

# side panel that contains the tool buttons
side_panel = ttk.Frame(master=root)
side_panel.grid(row=0, column=0, sticky="nsew")
side_panel.columnconfigure(0, weight=1)

# options panel that contains the tool's options
options_panel = ttk.Frame(master=root)
options_panel.grid(row=0, column=2, sticky="nsew")

# separators
ttk.Separator(master=root, orient="vertical").grid(row=0, column=1, sticky="ns")
ttk.Separator(master=root, orient="vertical").grid(row=0, column=3, sticky="ns")
ttk.Separator(master=root, orient="horizontal").grid(row=1, column=0, columnspan=5, sticky="ew")


# create command buttons in side panel
class Scripts(Enum):
    IMAGE_TO_MP3 = "image to mp3"
    ASCIIFY = "asciify"
    ASCHEATFY = "as-cheat-fy"
    GAN_IMAGE = "gan image"
    GAN_VIDEO = "gan video"


i = 0
for script in [e.value for e in Scripts]:
    ttk.Button(master=side_panel, text=script, command=lambda comm=script: on_click_command(comm)).grid(row=i, column=0, sticky="ew")
    i += 1

Globals.gui = DynamicGUI(root)


# clear the options panel when a different command button is clicked
def clear_options_panel():
    children = options_panel.grid_slaves()
    for child in children:
        child.destroy()


# config options panel for image to mp3
def config_image_to_mp3():
    ttk.Label(master=options_panel, text="path to image (png / jpg): ").grid(row=0, column=0, sticky="nw")
    image_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    image_path_entry.grid(row=1, column=0, sticky="nw")
    ttk.Label(master=options_panel, text="path to destination directory: ").grid(row=2, column=0, sticky="nw")
    mp3_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    mp3_path_entry.grid(row=3, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="convert").grid(row=4, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        ImageToMP3(image_path_entry.get(), mp3_path_entry.get())


# config options panel for asciifier
def config_asciify():
    ttk.Label(master=options_panel, text="path to image (png / jpg)").grid(row=0, column=0, sticky="nw")
    image_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    image_path_entry.grid(row=1, column=0, sticky="nw")
    ttk.Label(master=options_panel, text="path to destination directory: ").grid(row=2, column=0, sticky="nw")
    ascii_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    ascii_path_entry.grid(row=3, column=0, sticky="nw")
    static = IntVar()
    ttk.Checkbutton(master=options_panel, text="static palette", variable=static).grid(row=4, column=0, sticky="nw")
    color = IntVar()
    Radiobutton(master=options_panel, text="black on white", variable=color, value=0).grid(row=5, column=0, sticky="nw")
    Radiobutton(master=options_panel, text="white on black", variable=color, value=1).grid(row=6, column=0, sticky="nw")
    choices = AsciiResolution.get_option_names()
    resolution = StringVar(root)
    ttk.OptionMenu(options_panel, resolution, choices[0], *choices).grid(row=7, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="convert").grid(row=8, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        Asciifier(image_path_entry.get(), ascii_path_entry.get(), resolution=resolution.get(), static=(static.get() == 1), white_on_black=(color.get() == 1))


# config options panel for ascheatfier
def config_ascheatfy():
    ttk.Label(master=options_panel, text="path to image (png)\n or video (gif / mp4): ").grid(row=0, column=0, sticky="nw")
    image_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    image_path_entry.grid(row=1, column=0, sticky="nw")
    ttk.Label(master=options_panel, text="path to destination directory: ").grid(row=2, column=0, sticky="nw")
    ascii_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    ascii_path_entry.grid(row=3, column=0, sticky="nw")
    static = IntVar()
    ttk.Checkbutton(master=options_panel, text="static palette", variable=static).grid(row=4, column=0, sticky="nw")
    color = IntVar()
    Radiobutton(master=options_panel, text="black on white", variable=color, value=0).grid(row=5, column=0, sticky="nw")
    Radiobutton(master=options_panel, text="white on black", variable=color, value=1).grid(row=6, column=0, sticky="nw")
    choices = AscheatResolution.get_option_names()
    resolution = IntVar(root)
    ttk.OptionMenu(options_panel, resolution, choices[0], *choices).grid(row=7, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="convert").grid(row=8, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        Ascheatfier(image_path_entry.get(), ascii_path_entry.get(), resolution=resolution.get(),
                    static=(static.get() == 1), white_on_black=(color.get() == 1))


# config options panel for gan image
def config_gan_image():
    ttk.Label(master=options_panel, text="path to image (png): ").grid(row=0, column=0, sticky="nw")
    image_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    image_path_entry.grid(row=1, column=0, sticky="nw")
    ttk.Label(master=options_panel, text="path to destination directory: ").grid(row=2, column=0, sticky="nw")
    output_dir_path = ttk.Entry(master=options_panel, exportselection=0)
    output_dir_path.grid(row=3, column=0, sticky="nw")
    choices = ImDatasets.get_option_names()
    dataset = StringVar(root)
    ttk.OptionMenu(options_panel, dataset, choices[0], *choices).grid(row=4, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="generate").grid(row=5, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        GANImage(dataset=dataset.get(), input_path=image_path_entry.get(), output_path=output_dir_path.get())


# config options panel for gan video
def config_gan_video():
    ttk.Label(master=options_panel, text="path to video (gif or mp4): ").grid(row=0, column=0, sticky="nw")
    image_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    image_path_entry.grid(row=1, column=0, sticky="nw")
    ttk.Label(master=options_panel, text="path to destination directory: ").grid(row=2, column=0, sticky="nw")
    output_dir_path = ttk.Entry(master=options_panel, exportselection=0)
    output_dir_path.grid(row=3, column=0, sticky="nw")
    ttk.Label(master=options_panel, text="duration in minutes: ").grid(row=4, column=0, sticky="nw")
    duration_entry = ttk.Entry(master=options_panel, exportselection=0)
    duration_entry.grid(row=5, column=0, sticky="nw")
    dataset_choices = VidDatasets.get_option_names()
    dataset = StringVar(root)
    ttk.OptionMenu(options_panel, dataset, dataset_choices[0], *dataset_choices).grid(row=6, column=0, sticky="nw")
    speed_choices = Speed.get_option_names()
    speed = StringVar(root)
    ttk.OptionMenu(options_panel, speed, speed_choices[0], *speed_choices).grid(row=7, column=0, sticky="nw")
    transition_choices = TransitionTypes.get_option_names()
    transition = StringVar(root)
    ttk.OptionMenu(options_panel, transition, transition_choices[0], *transition_choices).grid(row=8, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="generate").grid(row=9, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        GANVideo(dataset=dataset.get(), input_path=image_path_entry.get(), output_path=output_dir_path.get(),
                 duration=duration_entry.get(), speed=speed.get(), transition_type=transition.get())


# onclick function of all command buttons in side panel
def on_click_command(button):
    Globals.gui.clear_status()
    clear_options_panel()
    if button == Scripts.IMAGE_TO_MP3.value:
        config_image_to_mp3()
    elif button == Scripts.ASCIIFY.value:
        config_asciify()
    elif button == Scripts.ASCHEATFY.value:
        config_ascheatfy()
    elif button == Scripts.GAN.value:
        config_gan_image()
    elif button == Scripts.GAN_VIDEO.value:
        config_gan_video()


root.mainloop()
