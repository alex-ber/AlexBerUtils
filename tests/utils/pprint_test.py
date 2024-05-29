import logging
import pytest
from alexber.utils.pprint import pformat

logger = logging.getLogger(__name__)

def assume(s1, s2):
    # Remove all whitespace characters from both strings
    s1_no_whitespace = ''.join(s1.split())
    s2_no_whitespace = ''.join(s2.split())


    pytest.assume(s1_no_whitespace == s2_no_whitespace)

input_d = {
        "more_info": [{
            "name": "Arthur",
            "last_name": "Doe",
        },
        {
            "name": "Sherlock",
            "last_name": "Holmes",
        }
        ],
        "answer": "The chance is zero for this",
    }


def test_standard_pprint(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')
    from pprint import pformat

    actual_s = pformat(input_d)
    exp_value_s = """{'answer': 'The chance is zero for this',
                     'more_info': [{'last_name': 'Doe', 'name': 'Arthur'},
                                   {'last_name': 'Holmes', 'name': 'Sherlock'}]}"""
    assume(exp_value_s, actual_s)

def test_standard_pprint_sort_dicts_false(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    from pprint import pformat

    actual_s = pformat(input_d, sort_dicts=False)
    exp_value_s = """{'more_info': [{'name': 'Arthur', 'last_name': 'Doe'},
                                    {'name': 'Sherlock', 'last_name': 'Holmes'}],
                     'answer': 'The chance is zero for this'}"""
    assume(exp_value_s, actual_s)

def test_my_pprint(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    actual_s = pformat(input_d)
    exp_value_s = """{'more_info': [{'name': 'Arthur', 'last_name': 'Doe'},
                                    {'name': 'Sherlock', 'last_name': 'Holmes'}],
                     'answer': 'The chance is zero for this'}"""
    assume(exp_value_s, actual_s)

def test_my_pprint_sort_dicts_false(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    actual_s = pformat(input_d, sort_dicts=False)
    exp_value_s = """{'more_info': [{'name': 'Arthur', 'last_name': 'Doe'},
                                    {'name': 'Sherlock', 'last_name': 'Holmes'}],
                     'answer': 'The chance is zero for this'}"""
    assume(exp_value_s, actual_s)

def test_my_pprint_sort_dicts_true(request, mocker):
    logger.info(f'{request._pyfuncitem.name}()')

    actual_s = pformat(input_d, sort_dicts=True)
    exp_value_s = """{'answer': 'The chance is zero for this',
                     'more_info': [{'last_name': 'Doe', 'name': 'Arthur'},
                                   {'last_name': 'Holmes', 'name': 'Sherlock'}]}"""
    assume(exp_value_s, actual_s)


if __name__ == "__main__":
    pytest.main([__file__])
