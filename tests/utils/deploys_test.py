import logging
import pytest
from importlib.resources import path
from pathlib import Path

from alexber.utils.deploys import split_path, load_config, add_to_zip_copy_function
from tests.utils.ymlparsers_test import ymlparsersSetup, ymlparsersCleanup, exp_config_d
from tests.utils.init_app_conf_test import initappconfFixture
import copy
import tempfile
import zipfile
import shutil
try:
    import alexber.utils.ymlparsers as ymlparsers
except ImportError:
    pass
logger = logging.getLogger(__name__)

class TestSplitPath(object):
    def test_split_path_intented(self, request):
        logger.info(f'{request._pyfuncitem.name}()')
        split_dirname = 'ymlparsers'
        pck = '.'.join(['tests_data', __package__, split_dirname])

        with path(pck, 'config.yml') as f:
            first_part, second_part = split_path(f, split_dirname)
            pytest.assume(f.parent==first_part)
            pytest.assume('config.yml'==str(second_part))

    def test_split_path_intented_path(self, request):
        logger.info(f'{request._pyfuncitem.name}()')
        split_dirname = 'ymlparsers'
        pck = '.'.join(['tests_data', __package__, split_dirname])

        with path(pck, 'config.yml') as f:
            first_part, second_part = split_path(Path(f), Path(split_dirname))
            pytest.assume(f.parent==first_part)
            pytest.assume('config.yml'==str(second_part))



    def test_split_path_absent_undefined_behaviour(self, request):
        logger.info(f'{request._pyfuncitem.name}()')
        pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

        with path(pck, 'config.yml') as f:
            with pytest.raises(BaseException):
                split_path(f, 'xxxnotfoundxxx')


    def test_split_path_absent_compount_name(self, request):
        logger.info(f'{request._pyfuncitem.name}()')
        pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

        with path(pck, 'config.yml') as f:
            with pytest.raises(BaseException):
                split_path(f, str(Path('ymlparsers', 'config.yml')))

    def test_split_path_None(self, request):
        logger.info(f'{request._pyfuncitem.name}()')
        split_dirname = 'ymlparsers'
        pck = '.'.join(['tests_data', __package__, split_dirname])

        with path(pck, 'config.yml') as f:
            with pytest.raises(BaseException, match='None'):
                split_path(f, None)

    def test_split_path_empty_str(self, request):
        logger.info(f'{request._pyfuncitem.name}()')
        split_dirname = 'ymlparsers'
        pck = '.'.join(['tests_data', __package__, split_dirname])

        with path(pck, 'config.yml') as f:
            with pytest.raises(BaseException):
                split_path(f, None)

    def test_split_path_twice_split_dir(self, request):
        logger.info(f'{request._pyfuncitem.name}()')
        split_dirname = 'tests'
        pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

        with path(pck, 'config.yml') as f:
            assert split_dirname in f.parts
            duplicate_dir_base = f.parent / split_dirname
            duplicate_dir_full_path = duplicate_dir_base / f.name
            first_part, second_part = split_path(duplicate_dir_full_path, split_dirname)

            pytest.assume(duplicate_dir_base==first_part)
            pytest.assume('config.yml'==str(second_part))

def check_config_yml(default_d, exp_d):


    app_d = default_d.get('app', None)
    exp_app_d = exp_d.get('app', None)

    inner_host_name = app_d.get('inner_host_name', None)
    exp_host_name = exp_app_d.get('inner_host_name', None)
    pytest.assume(exp_host_name==inner_host_name)
    cli_template = app_d.get('cli_template')
    pytest.assume('inner_host_name' in cli_template)
    pytest.assume(exp_d == default_d)

@pytest.mark.yml
def test_load_config(request, mocker, ymlparsersSetup, ymlparsersCleanup, initappconfFixture, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')

    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])
    exp_profiles=['dev']
    with path(pck, 'config.yml') as full_path:
        args = f"--general.config.file={full_path} --general.profiles={exp_profiles[0]}".split()
        config_path, default_d = load_config(None, args)

    pytest.assume(full_path == config_path)
    general_d = default_d.get('general', None)
    profiles = general_d.get('profiles', None)
    pytest.assume(exp_profiles == profiles)

    exp_d = copy.deepcopy(exp_config_d)
    exp_d['general']['profiles'] = exp_profiles

    check_config_yml(default_d, exp_d)

@pytest.mark.yml
def test_add_to_zip_copy_function(request, mocker,  ymlparsersSetup, ymlparsersCleanup, exp_config_d):
    logger.info(f'{request._pyfuncitem.name}()')
    split_dirname = 'ymlparsers'
    pck = '.'.join(['tests_data', __package__, 'ymlparsers'])

    with path(pck, 'config.yml') as full_path:


        with tempfile.TemporaryDirectory() as temp_dir:
            local_folder = Path(temp_dir)
            zip_path = local_folder / "my.zip"
            with zipfile.ZipFile(zip_path, mode="w") as zf:
                # not real copy, add to zip archive
                shutil.copytree(str(full_path.parent), str(local_folder / "xxxirrelevantxxx"),
                                ignore=shutil.ignore_patterns('__pycache__', 'venv', 'logs', '*.pyc', 'tmp*',
                                                              '.*', "__init__.py"),
                                copy_function=add_to_zip_copy_function(split_dirname=split_dirname, zf=zf),
                                symlinks=True, ignore_dangling_symlinks=True)
            with zipfile.ZipFile(zip_path, mode="r") as zf:
                entry_path = (Path(split_dirname) / 'config.yml').as_posix()
                entry_content_bytes = zf.read(str(entry_path))

                with ymlparsers.DisableVarSubst():
                    default_d = ymlparsers.load([entry_content_bytes.decode('utf-8')])

        check_config_yml(default_d, exp_config_d)



if __name__ == "__main__":
    pytest.main([__file__])

