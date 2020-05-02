## AlexBerUtils

AlexBerUtils is collection of the small utilities. See CHANGELOG.md for detail description.



### Getting Help


### QuickStart
```bash
pip3 install -U alex-ber-utils
```


### Installing from Github

```bash
python3 -m pip install -U https://github.com/alex-ber/AlexBerUtils/archive/master.zip
```
Optionally installing tests requirements.

```bash
python3 -m pip install -U https://github.com/alex-ber/AlexBerUtils/archive/master.zip#egg=alex-ber-utils[tests]
```

Or explicitly:

```bash
wget https://github.com/alex-ber/AlexBerUtils/archive/master.zip -O master.zip; unzip master.zip; rm master.zip
```
And then installing from source (see below).


### Installing from source
```bash
python3 -m pip install . # only installs "required"
```
```bash
python3 -m pip install .[tests] # installs dependencies for tests
```
```bash
python3 -m pip install .[md]   # installs multidispatcher (used in method_overloading_test.py)
```
```bash
python3 -m pip install .[fabric]   # installs fabric (used in fabs.py)
```
```bash
python3 -m pip install .[yaml]   # installs Yml related dependencies (used in ymlparsers.py, 
                                 # init_app_conf.py, emails.py)
```
```bash
python3 -m pip install .[pydotenv]   # installs pydotenv (optionally used in deploys.py)
```

#### Alternatively you install install from requirements file:
```bash
python3 -m pip install -r requirements.txt # only installs "required"
```
```bash
python3 -m pip install -r requirements-tests.txt # installs dependencies for tests
```
```bash
python3 -m pip install -r requirements-md.txt   # installs multidispatcher (used in method_overloading_test.py)
```
```bash
python3 -m pip install -r requirements-fabric.txt   # installs fabric (used in fabs.py)
```
```bash
python3 -m pip install -r requirements-yaml.txt   # installs Yml related dependencies (used in ymlparsers.py 
                                                  # init_app_conf.py, emails.py)
```
```bash
python3 -m pip install -r requirements-pydotenv.txt   # installs pydotenv (optionally used in deploys.py)
```


##

From the directory with setup.py
```bash
python3 setup.py test #run all tests
```

or

```bash

pytest
```

## Installing new version
See https://docs.python.org/3.1/distutils/uploading.html 

```bash
python3 setup.py sdist upload
```

## Requirements


AlexBerUtils requires the following modules.

* Python 3.7+

* PyYAML==5.1