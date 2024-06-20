"""
This module is usable in your deployment script. See also `deploys` module.

This module depends on some 3-rd party dependencies, in order to use it, you should have installed first. To do it
run `python -m pip install alex-ber-utils[fabric]`.

"""


import logging
logger = logging.getLogger(__name__)
from pathlib import PurePath

try:
    from fabric import Connection
except ImportError:
    import warnings

    warning = (
        "You appear to be missing some optional dependencies;"
        "please 'python -m pip install alex-ber-utils[fabric]'."
    )
    warnings.warn(warning, ImportWarning)
    raise




def _cp(self, remote_dir, local_file):
    """
    This is helper method that cp single file from local machine to remote (Posix) machine.
    If file exists on the remote machine, it will be overwritten.

    :param remote_dir: can be str or Path
    :param local_file:  can be str or Path
    """
    remote_dir_path = PurePath(remote_dir)
    self.run(f'mkdir -p {remote_dir_path.as_posix()}')
    #self.run('ls -l {}'.format(remote_dir))
    full_local_dir = PurePath(local_file)
    file_name = full_local_dir.name
    local_dir = full_local_dir.parent

    full_remote_dir = remote_dir_path / file_name
    self.run(f'rm -fr {full_remote_dir.as_posix()}')
    full_local_dir = PurePath(local_dir, file_name)
    result = self.put(local=full_local_dir.as_posix(), remote=remote_dir_path.as_posix())
    logger.info(f"Uploaded {result.local} to {result.remote}")

Connection.cp = _cp