import importlib
import logging
import inspect

logger = logging.getLogger(__name__)



#adopted from mock.mock._dot_lookup
def _dot_lookup(thing, comp, import_path):
    '''
    Recursively import packages (if needed) by dotes.
    '''
    try:
        return getattr(thing, comp)
    except AttributeError:
        importlib.import_module(import_path)
        return getattr(thing, comp)


#adopted from mock.mock._importer
def importer(target):
    '''
    Convert str to Python construct that target is represented.
    This method will recursively import packages (if needed)
    Following dot notation from left to right. If the component
    exists in packaga (is defined and imported) it will be used,
    otherwrise, it will be imported.

    Note: only compile-time construct is supported.
    Note: no instances will be returned from here, only classes.

    :param target: str to lookup
    :return: function/module/class, etc
    '''
    components = target.split('.')
    import_path = components.pop(0)
    thing = importlib.import_module(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing



def new_instance(target, *args, **kwargs):
    '''
    Convert str to Python construct that target is represented.
    This method will recursively import packages (if needed)
    Following dot notation from left to right. If the component
    exists in package (is defined and imported) it will be used,
    otherwrise, it will be imported.

    If target doesn't represent the class, it will be returned as is.
    If target is the class, instance of it will be created,
    args and kwargs will be passed in to appropriate
    __new__() / __init__() / __init_subclass__() methods.


    :param target:
    :param args:   - position args  for c-tor
    :param kwargs: - key-value args for c-tor
    :return:
    '''
    thing = importer(target)
    ret = thing
    if inspect.isclass(thing):
        ret = thing(*args, **kwargs)
    return ret