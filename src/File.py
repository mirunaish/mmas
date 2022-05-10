from os.path import isdir

from src.exceptions import IncorrectFileType


# input and output files used by scripts
class File:
    INPUT = "input"
    OUTPUT = "output"

    class Types:
        MATCH_INPUT = "match_input"
        PNG = "png"
        GIF = "gif"
        MP4 = "mp4"
        MP3 = "mp3"
        TXT = "txt"

    @staticmethod
    def uniformize_path(path):
        # if path was given with slashes, convert to backslash path
        path = path.replace('/', '\\')

        # if last character is a backslash, remove it
        if path[len(path) - 1] == '\\':
            path = path[:-1]

        return path

    @staticmethod
    def file_exists(path):
        try:
            file = open(path, 'r')
            file.close()
        except FileNotFoundError:
            return False

        return self.gui.file_locked(path)

    # constructor takes a path. file must then be configured as either input or output
    # doing it this way because file must somehow save this path information in script constructor
    # way before config is called / validation starts
    def __init__(self, path, gui):
        self.origin_path = self.uniformize_path(path)
        self.gui = gui
        self.directory_path = None
        self.file_name = None
        self.extension = None
        self.io = None

    # configure input file and verify that type is correct
    def config_input(self, input_types):
        # check that the file exists; raise error if not
        file = open(self.origin_path, 'r')
        file.close()

        self.directory_path = "\\".join(self.origin_path.split("\\")[:-1])  # remove file from path
        file = self.origin_path.split("\\").pop()  # split into path parts, get last part (filename + extension)
        self.extension = file.split(".").pop()  # split by dot, get last part (extension)
        self.file_name = ".".join(file.split(".")[:-1])  # remove file extension from file to get name

        # ensure file is valid extension
        if self.extension not in input_types:
            raise IncorrectFileType

        self.io = File.INPUT

    # configure output file with file name and extension
    def config_output(self, name, extension):
        # check that directory given in constructor exists
        if not isdir(self.origin_path):
            raise FileNotFoundError

        self.directory_path = self.origin_path
        self.extension = extension

        # if file name is used, put a number after it
        if self.file_exists(self.directory_path + '\\' + name + '.' + self.extension):
            index = 0
            while self.file_exists(self.directory_path + '\\' + name + '_' + str(index) + '.' + self.extension):
                index += 1
            self.file_name = name + '_' + str(index)
        else:
            self.file_name = name

        self.io = File.OUTPUT

    def get_full_path(self):
        return self.directory_path + '\\' + self.file_name + '.' + self.extension

    def acquire_lock(self):
        self.gui.lock_file(self.get_full_path())

    def release_lock(self):
        self.gui.unlock_file(self.get_full_path())
