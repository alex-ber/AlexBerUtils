


"""
A Python replacement for java.util.Properties class
This is modelled as closely as possible to the Java original.

Created - Anand B Pillai <abpillai@gmail.com>,
Update to Python 3 by Alex.
Also there are some tweeks that was done by Alex.
"""

# see https://code.activestate.com/recipes/496795-a-python-replacement-for-javautilproperties/
import sys
import re
import time
from collections import OrderedDict
import functools

class IllegalArgumentException(Exception):

    def __init__(self, lineno, msg):
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        s='Exception at line number %d => %s' % (self.lineno, self.msg)
        return s
                 
class Properties(object):
    """ A Python replacement for java.util.Properties """
    # Alex fix, handle ${}
    #curlies = re.compile('\\${.+?}')
    PLACEHOLDER_TOKEN = '$'

    def __init__(self, props=None):

        # Note: We don't take a default properties object
        # as argument yet

        # Dictionary of properties.
        # Alex changed {} to OrderedDict
        self._props = OrderedDict()
        # Dictionary of properties with 'pristine' keys
        # This is used for dumping the properties to a file
        # using the 'store' method
        # Alex changed {} to OrderedDict
        self._origprops = OrderedDict()

        # Dictionary mapping keys from property
        # dictionary to pristine dictionary
        # Alex changed {} to OrderedDict
        self._keymap = OrderedDict()
        # Alex changed {} to OrderedDict
        self._unresolved = OrderedDict()
        
        self.othercharre = re.compile(r'(?<!\\)(\s*\=)|(?<!\\)(\s*\:)')
        self.othercharre2 = re.compile(r'(\s*\=)|(\s*\:)')
        self.bspacere = re.compile(r'\\(?!\s$)')
        
    def __str__(self):
        s='{'
        for key,value in self._props.items():
            s = ''.join((s,key,'=',value,', '))

        s=''.join((s[:-2],'}'))
        return s

    def __parse(self, lines):
        """ Parse a list of lines and create
        an internal property dictionary """

        # Every line in the file must consist of either a comment
        # or a key-value pair. A key-value pair is a line consisting
        # of a key which is a combination of non-white space characters
        # The separator character between key-value pairs is a '=',
        # ':' or a whitespace character not including the newline.
        # If the '=' or ':' characters are found, in the line, even
        # keys containing whitespace chars are allowed.

        # A line with only a key according to the rules above is also
        # fine. In such case, the value is considered as the empty string.
         # In order to include characters '=' or ':' in a key or value,
        # they have to be properly escaped using the backslash character.

        # Some examples of valid key-value pairs:
        #
        # key     value
        # key=value
        # key:value
        # key     value1,value2,value3
        # key     value1,value2,value3 \
        #         value4, value5
        # key
        # This key= this value
        # key = value1 value2 value3
        
        # Any line that starts with a '#' is considerered a comment
        # and skipped. Also any trailing or preceding whitespaces
        # are removed from the key/value.
        
        # This is a line parser. It parses the
        # contents like by line.

        lineno=0
        i = iter(lines)

        for line in i:
            lineno += 1
            line = line.strip()
            # Skip null lines
            if not line: continue
            # Skip lines which are comments
            if line[0] == '#': continue
            # Some flags
            escaped=False
            # Position of first separation char
            sepidx = -1
            # A flag for performing wspace re check
            flag = 0
            # Check for valid space separation
            # First obtain the max index to which we
            # can search.
            m = self.othercharre.search(line)
            if m:
                first, last = m.span()
                start, end = 0, first
                flag = 1
                wspacere = re.compile(r'(?<![\\\=\:])(\s)')        
            else:
                if self.othercharre2.search(line):
                    # Check if either '=' or ':' is present
                    # in the line. If they are then it means
                    # they are preceded by a backslash.
                    
                    # This means, we need to modify the
                    # wspacere a bit, not to look for
                    # : or = characters.
                    wspacere = re.compile(r'(?<![\\])(\s)')        
                start, end = 0, len(line)
                
            m2 = wspacere.search(line, start, end)
            if m2:
                # print 'Space match=>',line
                # Means we need to split by space.
                first, last = m2.span()
                sepidx = first
            elif m:
                # print 'Other match=>',line
                # No matching wspace char found, need
                # to split by either '=' or ':'
                first, last = m.span()
                sepidx = last - 1
                # print line[sepidx]
                
                
            # If the last character is a backslash
            # it has to be preceded by a space in which
            # case the next line is read as part of the
            # same property
            while line[-1] == '\\':
                # Read next line
                nextline = i.next()
                nextline = nextline.strip()
                lineno += 1
                # This line will become part of the value
                line = line[:-1] + nextline

            # Now split to key,value according to separation char
            if sepidx != -1:
                key, value = line[:sepidx], line[sepidx+1:]
            else:
                key,value = line,''

            self.processPair(key, value)
            
    def processPair(self, key, value):
        """ Process a (key, value) pair """

        oldkey = key
        oldvalue = value
        
        # Create key intelligently
        keyparts = self.bspacere.split(key)
        # print keyparts

        strippable = False
        lastpart = keyparts[-1]

        if lastpart.find('\\ ') != -1:
            keyparts[-1] = lastpart.replace('\\','')

        # If no backspace is found at the end, but empty
        # space is found, strip it
        elif lastpart and lastpart[-1] == ' ':
            strippable = True

        key = ''.join(keyparts)
        if strippable:
            key = key.strip()
            oldkey = oldkey.strip()
        
        oldvalue = self.unescape(oldvalue)
        value = self.unescape(value)
        
        # Alex fix, handle ${}
        _regex ='\\${.+?}'
        if '$' != Properties.PLACEHOLDER_TOKEN:
            _regex = _regex[0:1] + Properties.PLACEHOLDER_TOKEN + _regex[2:]
        curlies = re.compile(_regex)
        found = curlies.findall(value)
        
        for f in found:
            srcKey = f[2:-1]
            if srcKey in self._props:
                value = value.replace(f, self._props[srcKey], 2)
        
        self._props[key] = value.strip()
        found = curlies.findall(value.strip())
        
        for f in found:
            srcKey = f[2:-1]
            if self._unresolved.has_key(srcKey):
                self._unresolved[srcKey] += [key]
            else:
                self._unresolved[srcKey] = [key]

        #End of Alex fix
        
        # Check if an entry exists in pristine keys
        if key in self._keymap:
            oldkey = self._keymap.get(key)
            self._origprops[oldkey] = oldvalue.strip()
        else:
            self._origprops[oldkey] = oldvalue.strip()
            # Store entry in keymap
            self._keymap[key] = oldkey
            
         # Alex fix, handle ${}
        if key in self._unresolved:
            for updateKey in self._unresolved[key]:
                self.processPair(updateKey, self._props[updateKey])
        
    def escape(self, value):

        # Java escapes the '=' and ':' in the value
        # string with backslashes in the store method.
        # So let us do the same.
        #Alex fix added r prefix to str
        newvalue = value.replace(':',r'\:')
        # Alex fix added r prefix to str
        newvalue = newvalue.replace('=',r'\=')

        return newvalue

    def unescape(self, value):

        # Reverse of escape
        # Alex fix added r prefix to str
        newvalue = value.replace(r'\:',':')
        # Alex fix added r prefix to str
        newvalue = newvalue.replace(r'\=','=')

        return newvalue    
        
    def load(self, stream):
        """ Load properties from an open file stream """

        #Alex disabled unneccesery stricked validations
        # For the time being only accept file input streams
        #if type(stream) is not file:
        #    raise TypeError('Argument should be a file object!')
        ## Check for the opened mode
        #if stream.mode != 'r':
        #    raise ValueError('Stream should be opened in read-only mode!')

        try:
            lines = stream.readlines()
            self.__parse(lines)
        except IOError as e:
            raise

    def getProperty(self, key):
        """ Return a property for the given key """
        
        return self._props.get(key,'')

    def setProperty(self, key, value):
        """ Set the property for the given key """

        if type(key) is str and type(value) is str:
            self.processPair(key, value)
        else:
            raise TypeError('both key and value should be strings!')

    def propertyNames(self):
        """ Return an iterator over all the keys of the property
        dictionary, i.e the names of the properties """

        return self._props.keys()

    def list(self, out=sys.stdout):
        """ Prints a listing of the properties to the
        stream 'out' which defaults to the standard output """

        out.write('-- listing properties --\n')
        for key,value in self._props.items():
            out.write(''.join((key,'=',value,'\n')))

    def store(self, out, header=""):
        """ Write the properties list to the stream 'out' along
        with the optional 'header' """

        if out.mode[0] != 'w':
            raise ValueError('Steam should be opened in write mode!')

        try:
            out.write(''.join(('#',header,'\n')))
            # Write timestamp
            tstamp = time.strftime('%a %b %d %H:%M:%S %Z %Y', time.localtime())
            out.write(''.join(('#',tstamp,'\n')))
            # Write properties from the pristine dictionary
            for prop, val in self._origprops.items():
                out.write(''.join((prop,'=',self.escape(val),'\n')))
                
            out.close()
        except IOError as e:
            raise

    # Alex changed name getPropertyDict() to current
    def as_dict(self):
        return self._props

    def __getitem__(self, name):
        """ To support direct dictionary like access """

        return self.getProperty(name)

    def __setitem__(self, name, value):
        """ To support direct dictionary like access """

        self.setProperty(name, value)
        
    def __getattr__(self, name):
        """ For attributes not found in self, redirect
        to the properties dictionary """

        try:
            return self.__dict__[name]
        except KeyError:
            if hasattr(self._props,name):
                return getattr(self._props, name)


#https://github.com/scanny/python-pptx/blob/master/pptx/util.py
class lazyproperty(object):
    """Decorator like @property, but evaluated only on first access.

    Like @property, this can only be used to decorate methods having only
    a `self` parameter, and is accessed like an attribute on an instance,
    i.e. trailing parentheses are not used. Unlike @property, the decorated
    method is only evaluated on first access; the resulting value is cached
    and that same value returned on second and later access without
    re-evaluation of the method.

    Like @property, this class produces a *data descriptor* object, which is
    stored in the __dict__ of the *class* under the name of the decorated
    method ('fget' nominally). The cached value is stored in the __dict__ of
    the *instance* under that same name.

    Because it is a data descriptor (as opposed to a *non-data descriptor*),
    its `__get__()` method is executed on each access of the decorated
    attribute; the __dict__ item of the same name is "shadowed" by the
    descriptor.

    While this may represent a performance improvement over a property, its
    greater benefit may be its other characteristics. One common use is to
    construct collaborator objects, removing that "real work" from the
    constructor, while still only executing once. It also de-couples client
    code from any sequencing considerations; if it's accessed from more than
    one location, it's assured it will be ready whenever needed.

    Loosely based on: https://stackoverflow.com/a/6849299/1902513.

    A lazyproperty is read-only. There is no counterpart to the optional
    "setter" (or deleter) behavior of an @property. This is critically
    important to maintaining its immutability and idempotence guarantees.
    Attempting to assign to a lazyproperty raises AttributeError
    unconditionally.

    The parameter names in the methods below correspond to this usage
    example::

        class Obj(object)

            @lazyproperty
            def fget(self):
                return 'some result'

        obj = Obj()

    Not suitable for wrapping a function (as opposed to a method) because it
    is not callable.
    """

    def __init__(self, fget):
        """*fget* is the decorated method (a "getter" function).

        A lazyproperty is read-only, so there is only an *fget* function (a
        regular @property can also have an fset and fdel function). This name
        was chosen for consistency with Python's `property` class which uses
        this name for the corresponding parameter.
        """
        # ---maintain a reference to the wrapped getter method
        self._fget = fget
        # ---adopt fget's __name__, __doc__, and other attributes
        functools.update_wrapper(self, fget)

    def __get__(self, obj, type=None):
        """Called on each access of 'fget' attribute on class or instance.

        *self* is this instance of a lazyproperty descriptor "wrapping" the
        property method it decorates (`fget`, nominally).

        *obj* is the "host" object instance when the attribute is accessed
        from an object instance, e.g. `obj = Obj(); obj.fget`. *obj* is None
        when accessed on the class, e.g. `Obj.fget`.

        *type* is the class hosting the decorated getter method (`fget`) on
        both class and instance attribute access.
        """
        # ---when accessed on class, e.g. Obj.fget, just return this
        # ---descriptor instance (patched above to look like fget).
        if obj is None:
            return self

        # ---when accessed on instance, start by checking instance __dict__
        value = obj.__dict__.get(self.__name__)
        if value is None:
            # ---on first access, __dict__ item will absent. Evaluate fget()
            # ---and store that value in the (otherwise unused) host-object
            # ---__dict__ value of same name ('fget' nominally)
            value = self._fget(obj)
            obj.__dict__[self.__name__] = value
        return value

    def __set__(self, obj, value):
        """Raises unconditionally, to preserve read-only behavior.

        This decorator is intended to implement immutable (and idempotent)
        object attributes. For that reason, assignment to this property must
        be explicitly prevented.

        If this __set__ method was not present, this descriptor would become
        a *non-data descriptor*. That would be nice because the cached value
        would be accessed directly once set (__dict__ attrs have precedence
        over non-data descriptors on instance attribute lookup). The problem
        is, there would be nothing to stop assignment to the cached value,
        which would overwrite the result of `fget()` and break both the
        immutability and idempotence guarantees of this decorator.

        The performance with this __set__() method in place was roughly 0.4
        usec per access when measured on a 2.8GHz development machine; so
        quite snappy and probably not a rich target for optimization efforts.
        """
        raise AttributeError("can't set attribute")  # pragma: no cover
