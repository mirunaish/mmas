import threading


# values shared by all scripts
from src.exceptions import FileLockedError


class Globals:
    working_folder_path = "res/working_folder"  # folder where some temporary things will be stored
    gui = None
    files_in_use = set()
    file_lock = threading.Lock()  # only one thread can access the file set at the same time

    # return true if file is currently locked by another thread
    @staticmethod
    def file_locked(file):
        Globals.file_lock.acquire(blocking=True)
        is_locked = file in Globals.files_in_use
        Globals.file_lock.release()
        return is_locked

    # add file to set of files currently in use
    @staticmethod
    def lock_file(file):
        if Globals.file_locked(file):
            raise FileLockedError

        Globals.file_lock.acquire(blocking=True)
        Globals.files_in_use.add(file)
        Globals.file_lock.release()

    # remove file from set of files currently in use
    @staticmethod
    def unlock_file(file):
        Globals.file_lock.acquire(blocking=True)
        try:
            Globals.files_in_use.remove(file)
        except KeyError:
            # file was not in use, ignore
            pass
        Globals.file_lock.release()
