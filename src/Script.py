import threading
from time import sleep
from src.File import File
from src.exceptions import FileLockedError


class Script(threading.Thread):

    # create a new Script object
    def __init__(self, gui, input_path=None, output_path=None):
        super().__init__(daemon=True)  # will continue to run even if main window is closed

        self.gui = gui
        self.preview = None  # the preview window i will put my preview image/text/etc in

        self.input_file = None
        if input_path is not None:
            self.input_file = File(input_path, self.gui)

        self.output_file = None
        if output_path is not None:
            self.output_file = File(output_path, self.gui)

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
                self.gui.update_status("the specified input file does not exist.", err=True)
                return

            # try to acquire lock on file
            try:
                self.input_file.acquire_lock()
            except FileLockedError:
                self.gui.update_status("this input file is currently in use.", err=True)
                return

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
                self.gui.update_status("destination folder does not exist.", err=True)
                return

            # try to acquire lock on file
            try:
                self.output_file.acquire_lock()
            except FileLockedError:
                self.gui.update_status("this input file is currently in use.", err=True)
                return

    def unconfig_io(self):
        self.input_file.release_lock()
        self.output_file.release_lock()

    # actual task to be done. to be overridden by children
    def convert(self):
        pass

    # can be overridden by children if necessary
    def config_preview(self):
        pass

    def run(self):
        # configure input and output files
        self.config_io()

        # create preview window
        self.preview = self.gui.new_tab(self._script_name, file=self.input_file.file_name)
        self.config_preview()

        self.convert()

        # un-configure input and output files (unlock)
        self.unconfig_io()

        # wait for a bit before making preview tab disappear
        sleep(5)
        self.gui.remove_tab(self.preview.name)
