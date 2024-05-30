#!/usr/bin/python3
import pytest

def main():
    pytest.main()

if __name__ == "__main__":
    main()

#docker exec -it $(docker ps -q -n=1) bash
#nano $HOME/.pypirc + chmod 600 $HOME/.pypirc
#use gihub login token for password
#python setup.py clean sdist upload
