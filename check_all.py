#!/usr/bin/python3
import pytest

def main():
    pytest.main()

if __name__ == "__main__":
    main()


#docker exec -it $(docker ps -q -n=1) bash
#export TWINE_USERNAME="__token__"
#export TWINE_PASSWORD="$PYPI_API_TOKEN"
#uv run python -m build
#uv run python -m twine upload dist/*
#python.use.targets.api=false



#rm -rf build dist *.egg-info