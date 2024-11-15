import os
import shutil

def get_pycache_dirpath_list(dirname, env_dirname='.venv'):
    dirname = os.path.normpath(dirname)
    pycache_dirpath_list = []

    for dir, sub_dir, filenames in os.walk(dirname):
        if dir.endswith("__pycache__"):
            all_dir = dir.split(os.sep)
            if env_dirname not in all_dir:
                pycache_dirpath = dir
                pycache_dirpath_list.append(pycache_dirpath)
    return pycache_dirpath_list

def del_dirpath(dirpath):
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath)
        return dirpath
    return None

def del_pycache(dirname, env_dirname='.venv'):
    pycache_dir_list = get_pycache_dirpath_list(dirname, env_dirname)
    del_pycache_dirpath_list = []
    for pycache_dir in pycache_dir_list:
        del_path = del_dirpath(pycache_dir)
        if del_path is not None:
            del_pycache_dirpath_list.append(del_path)
    return del_pycache_dirpath_list

if __name__=="__main__":
    del_pycache(".")