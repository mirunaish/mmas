# the file is locked
class FileLockedError(Exception):
    pass


# the file is of incorrect type / extension
class IncorrectFileType(Exception):
    pass
