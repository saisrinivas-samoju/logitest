import os
import shutil
from typing import Union, Optional
from pathlib import Path


def get_pycache_dirpath_list(dirname: Union[Path, str], env_dirname: str = '.venv') -> list:
    """Get directory path list of all the pycache directory in the given directory

    Args:
        dirname (Union[Path, str]): directory relative or absolute path to get the pycache directory path list
        env_dirname (str, optional): python environment folder will be excluded in this. Defaults to '.venv'.

    Returns:
        list: directory path list of all the pycache directory in the given directory
    """
    dirname = os.path.normpath(dirname)
    pycache_dirpath_list = []

    for dir, sub_dir, filenames in os.walk(dirname):
        if dir.endswith("__pycache__"):
            all_dir = dir.split(os.sep)
            if env_dirname not in all_dir:
                pycache_dirpath = dir
                pycache_dirpath_list.append(pycache_dirpath)
    return pycache_dirpath_list


def del_dirpath(dirpath: str) -> Optional[str]:
    """Delete the given directory path

    Args:
        dirpath (str): directory path to delete

    Returns:
        Optional[str]: delete directory path
    """
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath)
        return dirpath
    return None


def del_pycache(dirname: Union[Path, str], env_dirname: str = '.venv') -> list:
    """Delete pycache folders in the given directory path

    Args:
        dirname (Union[Path, str]): directory path in which all the pycache folders to be deleted
        env_dirname (str, optional): python environment folder will be excluded in this. Defaults to '.venv'.

    Returns:
        list: List of deleted pycache directory path list
    """
    pycache_dir_list = get_pycache_dirpath_list(dirname, env_dirname)
    del_pycache_dirpath_list = []
    for pycache_dir in pycache_dir_list:
        del_path = del_dirpath(pycache_dir)
        if del_path is not None:
            del_pycache_dirpath_list.append(del_path)
    return del_pycache_dirpath_list


if __name__ == "__main__":
    del_pycache(".")
