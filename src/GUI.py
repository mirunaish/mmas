from enum import Enum
from tkinter import ttk
from tkinter import *
from src.DynamicGUI import DynamicGUI
from src.scripts.Ascheatfier import Ascheatfier
from src.scripts.Asciifier import Asciifier
from src.scripts.GAN import Datasets, GAN
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
    GAN = "gan"


i = 0
for script in [e.value for e in Scripts]:
    ttk.Button(master=side_panel, text=script, command=lambda comm=script: on_click_command(comm)).grid(row=i, column=0, sticky="ew")
    i += 1

gui = DynamicGUI(root)


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
        ImageToMP3(gui, image_path_entry.get(), mp3_path_entry.get())


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
    choices = ['small (50)', 'medium (100)', 'big (500)']
    resolution = StringVar(root)
    ttk.OptionMenu(options_panel, resolution, choices[0], *choices).grid(row=7, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="convert").grid(row=8, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        Asciifier(gui, image_path_entry.get(), ascii_path_entry.get(), resolution=resolution.get(), static=(static.get() == 1), white_on_black=(color.get() == 1))


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
    choices = ['small (50)', 'medium (150)', 'big (300)']
    resolution = StringVar(root)
    ttk.OptionMenu(options_panel, resolution, choices[0], *choices).grid(row=7, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="convert").grid(row=8, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        Ascheatfier(gui, image_path_entry.get(), ascii_path_entry.get(), resolution=resolution.get(), static=(static.get() == 1), white_on_black=(color.get() == 1))


# config options panel for gan image
def config_gan_image():
    ttk.Label(master=options_panel, text="path to image (png)\n or video (gif / mp4): ").grid(row=0, column=0, sticky="nw")
    image_path_entry = ttk.Entry(master=options_panel, exportselection=0)
    image_path_entry.grid(row=1, column=0, sticky="nw")
    ttk.Label(master=options_panel, text="path to destination directory: ").grid(row=2, column=0, sticky="nw")
    output_dir_path = ttk.Entry(master=options_panel, exportselection=0)
    output_dir_path.grid(row=3, column=0, sticky="nw")
    choices = [e.value for e in Datasets]
    dataset = StringVar(root)
    ttk.OptionMenu(options_panel, dataset, choices[0], *choices).grid(row=7, column=0, sticky="nw")
    ttk.Button(master=options_panel, command=lambda: on_click_submit(), text="generate").grid(row=8, column=0, sticky="nw")

    # button's on_click function
    def on_click_submit():
        GAN(gui, dataset=dataset.get(), input_path=image_path_entry.get(), output_path=output_dir_path.get())


# onclick function of all command buttons in side panel
def on_click_command(button):
    gui.clear_status()
    clear_options_panel()
    if button == Scripts.IMAGE_TO_MP3.value:
        config_image_to_mp3()
    elif button == Scripts.ASCIIFY.value:
        config_asciify()
    elif button == Scripts.ASCHEATFY.value:
        config_ascheatfy()
    elif button == Scripts.GAN.value:
        config_gan_image()


root.mainloop()
