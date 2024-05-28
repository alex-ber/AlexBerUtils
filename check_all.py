#!/usr/bin/python3
import pytest

# from typing import Any
# import inspect
# import functools
#
#
# def decorator(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         """The decorated function is replaced with this one."""
#
#         def get_call_args_applying_defaults():
#             """Map both explicit and default arguments of decorated func call by param name."""
#             sig = inspect.signature(func)
#             call_args = dict(**dict(zip(sig.parameters, args)), **kwargs)
#             for param in sig.parameters.values():
#                 if param.name not in call_args and param.default is not param.empty:
#                     call_args[param.name] = param.default
#             return call_args
#
#         # -- call the partitioning function to get the elements --
#         elements = func(*args, **kwargs)
#
#         # -- look for a chunking-strategy argument and run the indicated chunker when present --
#         call_args = get_call_args_applying_defaults()
#
#         # return chunk_by_title(
#         #     elements,
#         #     combine_text_under_n_chars=call_args.get("combine_text_under_n_chars"),
#         #     max_characters=call_args.get("max_characters"),
#         #     multipage_sections=call_args.get("multipage_sections"),
#         #     new_after_n_chars=call_args.get("new_after_n_chars"),
#         #     overlap=call_args.get("overlap"),
#         #     overlap_all=call_args.get("overlap_all"),
#         # )
#
#
#     return wrapper
#
#
# return decorator

def main():
    pytest.main()

if __name__ == "__main__":
    main()

#docker exec -it $(docker ps -q -n=1) bash
#/etc/unlock_keyring.sh
#pip install keyrings.alt
#python -m keyring set https://upload.pypi.org/legacy/ alex-ber
#set $HOME/.pypirc
#python setup.py clean sdist upload