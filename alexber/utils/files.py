import logging

import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def join_files(f):
    """
    We will read all files that start from the same file name,
    and will write it's content to the specified file.

    :param f: output file, also pattern for other files to look on.
    :return:
    """
    output_file = Path(str(f))
    simple_filename = output_file.stem
    suffix = output_file.suffix
    p = output_file.parent

    gen = p.glob(f"{simple_filename}_*{suffix}")
    # see https://stackoverflow.com/a/27077437/1137529
    with open(str(output_file), 'w') as wfd:
        while True:
            try:
                partial_output = next(gen)
                with open(str(partial_output), 'r') as fd:
                    shutil.copyfileobj(fd, wfd)
            except StopIteration as e:
                break
