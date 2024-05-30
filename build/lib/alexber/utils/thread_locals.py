#inspired by https://stackoverflow.com/questions/1408171/thread-local-storage-in-python


def threadlocal_var(thread_locals, varname, factory, *args, **kwargs):
  v = getattr(thread_locals, varname, None)
  if v is None:
    v = factory(*args, **kwargs)
    setattr(thread_locals, varname, v)
  return v

def get_threadlocal_var(thread_locals, varname):
    v = threadlocal_var(thread_locals, varname, lambda : None)
    if v is None:
        raise ValueError(f"threadlocal's {varname} is not initilized")
    return v

def del_threadlocal_var(thread_locals, varname):
    try:
        delattr(thread_locals, varname)
    except AttributeError:
        pass
