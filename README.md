## AlexBerUtils

AlexBerUtils is collection of the small utilities. See CHANGELOG.md for detail description.



### Getting Help


### QuickStart
```bash
python -m pip install -U alex-ber-utils
```


### Installing from Github

```bash
python -m pip install -U https://github.com/alex-ber/AlexBerUtils/archive/master.zip
```
Optionally installing tests requirements.

```bash
python -m pip install -U https://github.com/alex-ber/AlexBerUtils/archive/master.zip#egg=alex-ber-utils[tests]
```

Or explicitly:

```bash
wget https://github.com/alex-ber/AlexBerUtils/archive/master.zip -O master.zip; unzip master.zip; rm master.zip
```
And then installing from source (see below).


### Installing from source
```bash
python -m pip install . # only installs "required"
```
```bash
python -m pip install .[tests] # installs dependencies for tests
```
```bash
python -m pip install .[piptools] # installs dependencies for pip-tools
```
```bash
python -m pip install .[fabric]   # installs fabric (used in fabs.py)
```
```bash
python -m pip install .[yml]   # installs Yml related dependencies 
                                # (used in ymlparsers.py, init_app_conf.py, deploys.py;
                                # optionally used in ymlparsers_extra.py, emails.py)
```
```bash
python -m pip install .[env]   # installs pydotenv (optionally used in deploys.py and mains.py)
```

#### Alternatively you install from requirements file:
```bash
python -m pip install -r requirements.txt # only installs "required"
```
```bash
python -m pip install -r requirements-tests.txt # installs dependencies for tests
```
```bash
python -m pip install -r requirements-piptools.txt # installs dependencies for pip-tools
```
```bash
python -m pip install -r requirements-fabric.txt   # installs fabric (used in fabs.py)
```
```bash
python -m pip install -r requirements-yml.txt   # installs Yml related dependencies 
                                                 # (used in ymlparsers.py, init_app_conf.py, deploys.py;
                                                 # optionally used in ymlparsers_extra.py, emails.py)
```
```bash
python -m pip install -r requirements-env.txt   # installs pydotenv (optionally used in deploys.py)
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
python setup.py test #run all tests
```

or

```bash

pytest
```

## Installing new version
See https://docs.python.org/3.1/distutils/uploading.html 


## Installing new version to venv
```bash
python -m pip uninstall --yes alex_ber_utils
python setup.py clean sdist bdist_wheel
python -m pip install --find-links=./dist alex_ber_utils==0.6.5
```

##Manual upload
```bash
#python setup.py clean sdist upload
```


## Requirements


AlexBerUtils requires the following modules.

* Python 3.8+

* PyYAML>=6.0.1

* packaging>=23.2
