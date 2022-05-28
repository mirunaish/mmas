import threading
from time import sleep
from src.File import File
from src.exceptions import IncorrectFileType
from src.globals import Globals


class OptionList:
    def __init__(self, options):
        self.options = options

    def get_option_names(self):
        return list(self.options.keys())

    def get_option_value(self, name):
        return self.options[name]


class Script(threading.Thread):

    # create a new Script object
    def __init__(self, input_path=None, output_path=None):
        super().__init__(daemon=True)  # will continue to run even if main window is closed

        self.preview = None  # the preview window i will put my preview image/text/etc in

        self.input_file = None
        if input_path is not None and input_path != "":
            self.input_file = File(input_path)

        self.output_file = None
        if output_path is not None and output_path != "":
            self.output_file = File(output_path)

        # to be overridden by children
        self._script_name = "none"
        self._input_types = []  # allowed input types
        self._output_type = "none"  # output type. if "MATCH_INPUT", is the same as input type

    # configure one input and one output file and validate them
    def config_io(self):
        # validate input file
        if self.input_file is not None:
            try:
                self.input_file.config_input(self._input_types)
            except FileNotFoundError:
                Globals.gui.update_status("the specified input file does not exist.", err=True)
                raise ValueError
            except IncorrectFileType:
                Globals.gui.update_status("the specified input file is of incorrect type.", err=True)
                raise ValueError

            if self.input_file.is_locked():
                Globals.gui.update_status("this input file is currently in use.", err=True)
                raise ValueError

        # if set to match input, match input
        if self._output_type == File.Types.MATCH_INPUT:
            self._output_type = self.input_file.extension
        # set output file name
        file_name = (self.input_file.file_name + '_' if self.input_file is not None else '') + self._script_name

        # validate output file
        if self.output_file is not None:
            try:
                self.output_file.config_output(file_name, self._output_type)
            except FileNotFoundError:
                Globals.gui.update_status("destination folder does not exist.", err=True)
                raise ValueError

            if self.output_file.is_locked():
                Globals.gui.update_status("this output file is currently in use.", err=True)
                raise ValueError

        # acquire locks
        if self.input_file is not None:
            self.input_file.acquire_lock()
        if self.output_file is not None:
            self.output_file.acquire_lock()

    # can be overridden by children
    def validate_arguments(self):
        pass

    def unconfig_io(self):
        if self.input_file is not None:
            self.input_file.release_lock()
        if self.output_file is not None:
            self.output_file.release_lock()

    # actual task to be done. to be overridden by children
    def convert(self):
        pass

    # can be overridden by children if necessary
    def config_preview(self):
        pass

    def run(self):
        # configure input and output files
        try:
            self.config_io()
            self.validate_arguments()
        except ValueError:
            return

        # create preview window
        self.preview = Globals.gui.new_tab(self._script_name, file=self.output_file.file_name)
        self.preview.progress_amount(0)
        self.preview.progress_update("loading...")
        self.config_preview()

        self.convert()

        # un-configure input and output files (unlock)
        self.unconfig_io()

        # wait for a bit before making preview tab disappear
        sleep(5)
        Globals.gui.remove_tab(self.preview.name)
