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
python3 -m pip install .[test] # installs dependencies for tests
```
```bash
python3 -m pip install .[md]   # installs multidispatcher (used in method_overloading_test.py)
```
##

From the directory with setup.py
```bash
python3 setup.py test #run all tests
```
```bash
pytest
```



## Requirements


AlexBerUtils requires the following modules.

* Python 3.7+

* PyYAML==5.1