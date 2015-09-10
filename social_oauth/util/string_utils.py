# -*- coding: utf-8 -*-
"""
Utilities for string manipulation.
"""
import string
import re

ALL_NUMBER_RE = re.compile(r'^\d+$')
USERNAME_RE = re.compile(u'^[\u4e00-\u9fa5-\w]+$')
PHONE_NUMBER_RE = re.compile(r'^1[0-9]{10}$')



def str_to_bool(str):
    """
    Converts "true" (case-insensitive) to the boolean True.
    Everything else will return False (including None).

    An error will be thrown for non-string input (besides None).
    """
    return False if str is None else str.lower() == "true"


def string_len(_str, one_length_strings=u'{}{}-_'.format(string.digits, string.ascii_letters)):
    '''
    查看一个字符串的字符长度, one_length_strings中的字符为1, 其余为2
    '''
    length = 0
    for s in _str:
        if s in one_length_strings:
            length += 1
        else:
            length += 2
    return length


def _has_non_ascii_characters(data_string):
    """
    Check if provided string contains non ascii characters

    :param data_string: basestring or unicode object
    """
    try:
        data_string.encode('ascii')
    except UnicodeEncodeError:
        return True

    return False

def get_implicit_phone_number(phone_number):
    prefix = phone_number[:3]
    suffix = phone_number[-4:]
    implicit_phone_number = prefix + '****' + suffix
    return implicit_phone_number

def get_implicit_email(email):
    suffix = email.split('@')[1]
    first_char = email[0]
    last_char = email.split('@')[0][-1]
    implicit_email = first_char + '****' + last_char + '@' + suffix
    return implicit_email
