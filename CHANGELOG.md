# Changelog
All notable changes to this project will be documented in this file.

\#https://pypi.org/manage/project/alex-ber-utils/releases/

## [Unrelased]

## [0.4.1] - 2020-04-02
### Changed
**BREAKING CHANGE** I highly recommend not to use 0.3.X versions.

- *Limitation:*:

`mains` module wasn't tested with frozen python script (frozen using py2exe). 
 
- module `warns` is droped
- module `mains` is rewritten. Function `initConf` is dropped entirely.
- module `mains` now works with logger and with warnings (it was wrong decision to work with warinings).


## [0.3.4] - 2020-04-02
### Changed
- CHANGELOG.md fixed
- `warns` module bug fixed, now warnings.warn() works.
- FixabscwdWarning is added to simplify warnings disabling.
- Changing how `mains` module use `warns`.


## [0.3.3] - 2020-04-02
### Changed
- CHANGELOG.md fixed
- Article about `warns` module is published. See https://medium.com/@alex_ber/integrating-pythons-logging-and-warnings-packages-7748a760cde3


## [0.3.2] - 2020-04-01
### Changed
- To REAMDE.md add `Installing new version` section
- Fix typo in REAMDE.md (tests, not test). 
- Fixing bug: now, you're able to import package in the Python interpreter (`setups.py` fixed)
- Fixing bug: `warns` module now doesn't change log_level in the preconfigured logger in any cases.
- **BREAKING CHANGE**: In`mains` module method `warnsInitConfig()` was renamed to `mainInitConfig()` 
Also singature was changed.  
- `mains` module minor refactored.

 
### Added
- Unit tests are added for `warns` module 
- Unit tests are added for `mains` module

## [0.3.1] - 2020-04-01
### Changed
- Tests minor improvements.
- Excluded tests, data from setup.py (from being installed from the sdist.)
- Created MANIFEST.in
 

### Added
- `warns `module is added:
 
It provides better integration between warnings and logger. 
Unlike `logging._showwarning()` this variant will always go through logger. 

`warns.initConfig()` has optional file parameter (it's file-like object) to redirect warnings. 
Default value is `sys.stderr`.
 
If logger for `log_name` (default is `py.warnings`) will be configured before call to `showwarning()` method, 
than warning will go to the logger's handler with `log_level` (default is `logging.WARNING`).

If logger for `log_name` (default is `py.warnings`) willn't be configured before call to showwarning() method, 
than warning will be done to `file` (default is `sys.stderr`) with `log_level` (default is `logging.WARNING`).
 
- `main` module is added:

`main.fixabscwd()` changes `os.getcwd()` to be the directory of the `__main__` module.

`main.warnsInitConfig()` reexports `warns.initConfig()` for convenience.   



### Added
- Tests for alexber.utils.thread_locals added.

## [0.2.5] - 2019-05-22
### Changed
- Fixed bug in UploadCommand, git push should be before git tag.


## [0.2.4] - 2019-05-22
### Changed
- Fixed bug in setup.py, incorrect order between VERSION and UploadCommand (no tag was created on upload)

## [0.2.1] - 2019-05-22
### Changed
- setup url fixed.
- Added import of Enum to alexber.utils package.

## [0.2.0] - 2019-05-22
### Changed
- setup.py - keywords added.

## [0.1.1] - 2019-05-22
### Changed
- README.md fixed typo.

## [0.1.0] - 2019-05-22
### Changed
- alexber.utils.UploadCommand - bug fixed, failed on git tag, because VERSION was undefined.


## [0.0.1] - 2019-05-22
### Added
- alexber.utils.StrAsReprMixinEnum - Enum Mixin that has __str__() equal to __repr__().
- alexber.utils.AutoNameMixinEnum-  Enum Mixin that generate value equal to the name.
- alexber.utils.MissingNoneMixinEnum - Enum Mixin will return None if value will not be found.
- alexber.utils.LookUpMixinEnum - Enim Mixin that is designed to be used for lookup by value. 

  If lookup fail, None will be return. Also, __str__() will return the same value as __repr__().
- alexber.utils.threadlocal_var, get_threadlocal_var, del_threadlocal_var. 

  Inspired by https://stackoverflow.com/questions/1408171/thread-local-storage-in-python

- alexber.utils.UploadCommand -  Support setup.py upload.

    UploadCommand is intented to be used only from setup.py

    It's builds Source and Wheel distribution.

    It's uploads the package to PyPI via Twine.

    It's pushes the git tags.

- alexber.utils.uuid1mc is is a hybrid between version 1 & version 4. This is v1 with random MAC ("v1mc").

    uuid1mc() is deliberately generating v1 UUIDs with a random broadcast MAC address.

    The resulting v1 UUID is time dependant (like regular v1), but lacks all host-specific information (like v4).
    
    Note: somebody reported that ran into trouble using UUID1 in Amazon EC2 instances.
    

- alexber.utils.importer.importer - Convert str to Python construct that target is represented.
- alexber.utils.importer.new_instance - Convert str to Python construct that target is represented. 
args and kwargs will be passed in to appropriate __new__() / __init__() / __init_subclass__() methods.
- alexber.utils.inspects.issetdescriptor - Return true if the object is a method descriptor with setters.

  But not if ismethod() or isclass() or isfunction() are true.
- alexber.utils.inspects.ismethod - Return false if object is not a class and not a function. 
Otherwise, return true iff signature has 2 params.
- alexber.utils.parsers.safe_eval - The purpose of this function is convert numbers from str to correct type.
  
  This function support convertion of built-in Python number to correct type (int, float)
  
  This function doesn't support decimal.Decimal or datetime.datetime or numpy types.  
- alexber.utils.parsers.is_empty - if value is None returns True.
   
   if value is empty iterable (for example, empty str or emptry list),returns true otherwise false.

   Note: For not iterable values, behaivour is undefined.
- alexber.utils.parsers.parse_boolean - if value is None returns None.

    if value is boolean, it is returned as it is.
    if value is str and value is equals ignoring case to "True", True is returned.
    if value is str and value is equals ignoring case to "False", False is returned.

    For every other value, the answer is undefined. 



- alexber.utils.props.Properties - A Python replacement for java.util.Properties class
   
   This is modelled as closely as possible to the Java original.
   
   Created - Anand B Pillai <abpillai@gmail.com>.
   
   Update to Python 3 by Alex.
   
   Also there are some tweeks that was done by Alex.

<!--
### Changed
### Removed
-->
