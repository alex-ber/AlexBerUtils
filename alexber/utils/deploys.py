"""
This module is usable in your deployment script. See also `fabs` module.

See here https://medium.com/analytics-vidhya/my-ymlparsers-module-88221edf16a6 for documentation.

This module depends on some 3-rd party dependencies, in order to use it, you should have installed first. To do it
run `python -m pip install alex-ber-utils[yml]`.
"""

from collections import OrderedDict
from pathlib import Path
from collections import deque
try:
    import alexber.utils.ymlparsers as ymlparsers
except ImportError:
    pass

from .init_app_conf import merge_list_value_in_dicts, conf
from .parsers import is_empty, parse_sys_args


def split_path(filename, split_dirname):
    """
    Split filename in 2 part parts by split_dirname.
    first_part will ends with split_dirname.
    second_part will start immediately after split_dirname.

    if split_dirname is not in filename or split_dirname is None, the behaviour is undefined.
    if split_dirname exists twice in the path, the last one will be used for splitting.

    :param filename: path to filename, can be relative or absolute.
    :param split_dirname: directory name in filename that will be used to split the path
    :return: (first_part, second_part) - such that first_part+second_part is absolute path.

    """
    if split_dirname is None:
        raise FileNotFoundError("can't split on None")

    parts = Path(filename).parts
    split_dirname = str(split_dirname)


    if split_dirname not in parts:
        raise FileNotFoundError(f"{split_dirname} is not found in {filename}")
    length = len(parts)

    use = False
    second_parts = deque(maxlen=length)
    first_parts = deque(maxlen=length)
    for part in reversed(parts):
        if part == split_dirname:
            use = True
        if use:
            first_parts.appendleft(part)
        else:
            second_parts.appendleft(part)


    return Path(*first_parts), Path(*second_parts)

def add_to_zip_copy_function(split_dirname=None, zf=None):
    """
    Factory method that returns closure that can be used as copy_function param in shutil.copytree()

    :param split_dirname: path from this directory and below will be used in archive.
    :param zf: zipfile.ZipFile
    :return:
    """
    def add_to_zip_file(src,dst):
        """
        Closure that can be used as copy_function param in shutil.copytree()
        shutil.copytree() is used to add from src to archive with entries evaluted according to split_dirname.

        :param src: soource file to use in entry in archive
        :param dst: ignored, see split_dirname in enclused function
        :return:
        """
        _, last_parts = split_path(src, split_dirname)
        dest_path = Path(split_dirname) / last_parts
        zf.write(str(src), str(dest_path))
    return add_to_zip_file

def load_config(argumentParser=None, args=None):
    """
    Simplified method for parsing yml configuration file with optionally overrided profiles only.
    See alexber.utils.init_app_conf.parse_config() for another variant.

    :param argumentParser with instruction how to interpret args. If None, the default one will be instantiated.
    :param args: if not None will be used instead of sys.argv
    :return:
    """
    if ymlparsers.HiYaPyCo.jinja2ctx is None:
        raise ValueError("ymlparsers.HiYaPyCo.jinja2ctx can't be None")

    params, sys_d = parse_sys_args(argumentParser, args)
    config_file = params.config_file
    full_path = Path(config_file).resolve()  # relative to cwd

    with ymlparsers.DisableVarSubst():
        default_d = ymlparsers.load([str(full_path)])

    profiles = merge_list_value_in_dicts(sys_d, default_d, conf.GENERAL_KEY, conf.PROFILES_KEY)
    b = is_empty(profiles)
    if not b:
        # merge to default_d
        general_d = default_d.setdefault(conf.GENERAL_KEY, OrderedDict())
        general_d[conf.PROFILES_KEY] = profiles
        return full_path, default_d

