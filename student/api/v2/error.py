# -*- coding: utf-8 -*-
from rest_framework import status
from rest_framework.response import Response

# System error
SYSTEM_ERROR = 10001
REMOTE_SERVICE_ERROR = 10002

# Common error
MISSING_PARAMETER = 20001
INVALID_PARAMETER = 20002
APIException = 20003
MethodNotAllowed = 20004
NotAuthenticated = 20005
PermissionDenied = 20006
UnsupportedMediaType = 20007
AuthenticationFailed = 20008
NotAcceptable = 20009
ParseError = 20010
Throttled = 20011

# Course error
INVALID_ENROLLMENT = 30001
USER_NOT_ENROLLED = 30002
COURSES_FOLLOW_FAILED = 30010

# 登录注册有关错误 40000

REGISTER_FAILED = 40000

USERNAME_LENGHT_TOO_SHORT = 40010
USERNAME_LENGHT_TOO_LONG = 40011
USERNAME_CANT_ALL_NUMBER = 40012
USERNAME_FORMAT_ERROR = 40013
USERNAME_EXIST = 40014

# 密码相关
PASSWORD_LENGHT_TOO_SHORT = 40020
PASSWORD_LENGHT_TOO_LONG = 40021
PASSWORD_ERROR = 40022
PASSWORD_ALREADY_BIND = 40023
PASSWORD_ILLEGAL = 40024

# email相关
EMAIL_FORMAT_ERROR = 40030
EMAIL_EXIST = 40031
EMAIL_CHANGE_FAILED = 40032
EMAIL_ALREADY_BIND = 40033
EMAIL_NOT_BIND = 40034

# 手机验证码相关
SMS_FAILED = 40040
SMS_TOO_FREQUENTLY = 40041
SMS_OUT_OF_DATE = 40042
SMS_VERIFICATION_FAILED = 40043
SMS_VERIFICATION_SUCCESS = 40044
SMS_TOO_FREQUENTLY = 40045
SMS_SEND_FAILED = 40046
AUTHTOKEN_FORMAT_ERROR = 40047
AUTHTOKEN_OUT_OF_DATE = 40047

# 手机号码相关
PHONE_NUMBER_FORMAT_ERROR = 40050
PHONE_NUMBER_EXIST = 40051
PHONE_NUMBER_DONT_EXIST = 40052
PHONE_ALREADY_BIND = 40053
PHONE_NOT_BIND = 40054

# 三方登陆相关
SOCIAL_OAUTH_FAILED = 40060
SOCIAL_OAUTH_LOGIN_FAILED = 40061
SOCIAL_OAUTH_AUTH_ALREADY_ASSOCIATED = 40062
SOCIAL_OAUTH_NOT_ALLOWED_TO_DISCONNECT = 40063

class Error(Exception):

    def __init__(self, err_code, err_message='Internal Server Error', status_code=status.HTTP_400_BAD_REQUEST):
        self.err_code = err_code
        self.err_message = err_message
        self.status_code = status_code

    def __unicode__(self):
            return u'[Error] %d: %s(%d)' % (self.err_code, self.err_message, self.status_code)

    def getResponse(self):
        return ErrorResponse(self.err_code, self.err_message, self.status_code)


def ErrorResponse(err_code=SYSTEM_ERROR, err_message='Internal Server Error', status=status.HTTP_400_BAD_REQUEST):
    err = {
        'error_code': err_code,
        'error': err_message,
    }
    return Response(err, status)
