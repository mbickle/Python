import os, stat
import datetime
import shutil

def __init__(self):
    pass
    
def format_filesize(size):
    if size < 0:
        raise ValueError("Size must be greater than 0.")

    step = 1024
    unit = 'B'

    if size / step >= 1:
        size /= step
        unit = 'KB'

    if size / step >= 1:
        size /= step
        unit = 'MB'

    if size / step >= 1:
        size /= step
        unit = 'GB'

    if size / step >= 1:
        size /= step
        unit = 'TB'

    size = round(size, 1)
    return str(size) + ' ' + unit

def get_diskusage(path):
    disk_usage = shutil.disk_usage(path)
    return disk_usage

def remove_ageditems(path, age, force = False, emptyFolder = False):
    files = get_files(path)
    agedfiles_removed = 0
    for file in files:
        if is_file_older_than_age(file, age):
            try:
                if force == True:
                    remove_readonly(file)

                os.remove(file)
                agedfiles_removed = agedfiles_removed + 1
            except OSError as error:
                print(error)

    if emptyFolder == True:
       remove_empty_folders(path)

    return agedfiles_removed

def remove_empty_folders(path):
    deleted = set()

    for current_dir, subdirs, files in os.walk(path, topdown=False):
        has_subdirs = any(
            current_dir for subdir in subdirs
            if os.path.join(current_dir, subdir) not in deleted
        )
        
        if not any(files) and not has_subdirs:
            os.rmdir(current_dir)
            deleted.add(current_dir)

def remove_readonly(path):
    os.chmod(path, stat.S_IWRITE)

def is_file_older_than_age(file, age):
    if (os.path.isfile(file)):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=int(age))
        file_time =  datetime.datetime.fromtimestamp(os.path.getmtime(file))
        return file_time < cutoff

def get_files(path):
    files = []
    if os.path.exists(path):
        for f in os.listdir(path):
            if os.path.isfile(os.path.join(path, f)):
                files.append(os.path.join(path, f))
    return files

def get_folders(path):
    folders = []

    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                folders.append(os.path.join(root, dir))
    
    return folders

def get_files_recursive(path):
    files = []

    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for file in files:
                files.append(os.path.join(root, file))

    return files

def is_number(val):
    try:
        float(val)
        return True
    except ValueError:
        return False