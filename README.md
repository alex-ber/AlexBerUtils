## AlexBerUtils

AlexBerUtils is collection of the small utilities. See CHANGELOG.md for detail description.



### Getting Help


### QuickStart
```bash
python3 -m pip install -U alex-ber-utils
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
python3 -m pip install .[piptools] # installs dependencies for pip-tools
```
```bash
python3 -m pip install .[md]   # installs multidispatcher (used in method_overloading_test.py)
```
```bash
python3 -m pip install .[fabric]   # installs fabric (used in fabs.py)
```
```bash
python3 -m pip install .[yml]   # installs Yml related dependencies 
                                # (used in ymlparsers.py, init_app_conf.py, deploys.py;
                                # optionally used in ymlparsers_extra.py, emails.py)
```
```bash
python3 -m pip install .[env]   # installs pydotenv (optionally used in deploys.py and mains.py)
```

#### Alternatively you install from requirements file:
```bash
python3 -m pip install -r requirements.txt # only installs "required"
```
```bash
python3 -m pip install -r requirements-tests.txt # installs dependencies for tests
```
```bash
python3 -m pip install -r requirements-piptools.txt # installs dependencies for pip-tools
```
```bash
python3 -m pip install -r requirements-md.txt   # installs multidispatcher (used in method_overloading_test.py)
```
```bash
python3 -m pip install -r requirements-fabric.txt   # installs fabric (used in fabs.py)
```
```bash
python3 -m pip install -r requirements-yml.txt   # installs Yml related dependencies 
                                                 # (used in ymlparsers.py, init_app_conf.py, deploys.py;
                                                 # optionally used in ymlparsers_extra.py, emails.py)
```
```bash
python3 -m pip install -r requirements-env.txt   # installs pydotenv (optionally used in deploys.py)
```

### Using Docker
`alexberkovich/AlexBerUtils:latest`  contains all `AlexBerUtils` dependencies.
This Dockerfile is very simple, you can take relevant part for you and put them into your Dockerfile.

##
Alternatively, you can use it as base Docker image for your project and add/upgrade 
another dependencies as you need.

For example:

```Dockerfile
FROM alexberkovich/alex_ber_utils:latest

COPY requirements.txt etc/requirements.txt

RUN set -ex && \
    #latest pip,setuptools,wheel
    pip install --upgrade pip setuptools wheel && \
    pip install alex_ber_utils 
    pip install -r etc/requirements.txt 

CMD ["/bin/sh"]
#CMD tail -f /dev/null
```

where `requirements.txt` is requirements for your project.

  

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


## Installing new version to venv
```bash
python38 -m pip uninstall --yes alex_ber_utils
python38 setup.py clean sdist bdist_wheel
python38 -m pip install --find-links=./dist alex_ber_utils==0.6.5
```

##Manual upload
```bash
#python setup.py clean sdist upload
```


## Requirements


AlexBerUtils requires the following modules.

* Python 3.6+

* PyYAML>=6.0.1
