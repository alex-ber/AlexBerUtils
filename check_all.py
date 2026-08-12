#!/usr/bin/python3
import pytest

def main():
    pytest.main()

if __name__ == "__main__":
    main()

#docker exec -it $(docker ps -q -n=1) bash
#nano $HOME/.pypirc
# [distutils]
# index-servers =
#     pypi
#
# [pypi]
# repository = https://upload.pypi.org/legacy/
# username = __token__
# password = pypi-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

#chmod 600 $HOME/.pypirc
#use gihub login token for password
#uv run python setup.py clean sdist upload
#python.use.targets.api=false


