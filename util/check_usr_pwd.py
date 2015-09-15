# -*- coding:utf8 -*-
from string_utils import string_len


def check_username(username):
    sensitive_username = ("管理员", "工作人员", "学堂在线", "学堂", "版主", "测试", "admin", "administrator")
    if username in sensitive_username:
        return -1
    if u"管理员" in username:
        return -1
    if u"admin" in username:
        return -1
    if string_len(username) > 16:
        return -2

    return 0


def check_password(password):
    weak_password = ("112233", "123123", "123321", "abcabc", "abc123", "a1b2c3", "aaa111", "123qwe", "qwerty", "qweasd", "admin", "password", "p@ssword", "passwd", "iloveyou", "5201314", "asdfghjkl")
    if password in weak_password:
        return -1

    if " " in password:
        return -2
    
    if judge_continuous_string(password) == -1:
        return -3

    if len(password) < 6 or len(password) > 20:
        return -4

    return 0


def judge_continuous_string(string):
    first = string[0]
    count = 0
    for n in range(1, len(string)):
        if first != string[n]:
            return 0
        else:
            count = count + 1
    
    if count == n:
        return -1

'''
print check_username("1111111111111111111")
print check_password("11")
'''
