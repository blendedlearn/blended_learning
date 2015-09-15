# -*- coding: utf-8 -*-
import time
import traceback
import sys
import logging

from copy import copy
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.exceptions import (
        APIException, MethodNotAllowed,
        NotAuthenticated, PermissionDenied, UnsupportedMediaType,
        AuthenticationFailed, NotAcceptable, ParseError, Throttled
)
import rest_framework.views as views
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django_future.csrf import csrf_exempt
import api.v2.error as error


log = logging.getLogger(__name__)


class ApiKeyHeaderPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        api_key = getattr(settings, "EDX_API_KEY", None)
        return settings.DEBUG or request.META.get("HTTP_X_EDX_API_KEY") == api_key


def custom_exception_handler(exc):
    """ Handle the special errors """
    log.warn("api error: %s" % exc)

    if isinstance(exc, NotAuthenticated):
        log.warn("NotAuthenticated: %s" % exc)
        return error.ErrorResponse(error.NotAuthenticated, "NotAuthenticated: 未登录")

    if isinstance(exc, PermissionDenied):
        log.warn("PermissionDenied: %s" % exc)
        return error.ErrorResponse(error.PermissionDenied, "PermissionDenied: 没有对应权限")

    if isinstance(exc, AuthenticationFailed):
        log.warn("AuthenticationFailed: %s" % exc)
        return error.ErrorResponse(error.AuthenticationFailed, "AuthenticationFailed: 认证失败")

    if isinstance(exc, error.Error):
        log.warn("Custom Error: %s" % exc)
        return error.ErrorResponse(exc.err_code, exc.err_message, status=exc.status_code)

    log.exception(exc)

    if isinstance(exc, KeyError):
        log.warn("KeyError: %s" % exc)
        return error.ErrorResponse(error.MISSING_PARAMETER, "Missing parameter")

    if isinstance(exc, ValueError) or isinstance(exc, AssertionError):
        log.warn("ValueError, AssertionError: %s" % exc)
        return error.ErrorResponse(error.INVALID_PARAMETER, "Parameter type error")

    if isinstance(exc, ObjectDoesNotExist):
        log.warn("ObjectDoesNotExist: %s" % exc)
        return Response(status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, MethodNotAllowed):
        log.warn("MethodNotAllowed: %s" % exc)
        return error.ErrorResponse(error.MethodNotAllowed, "MethodNotAllowed: api调用方式错误")

    if isinstance(exc, UnsupportedMediaType):
        log.warn("UnsupportedMediaType: %s" % exc)
        return error.ErrorResponse(error.UnsupportedMediaType, "UnsupportedMediaType: 不支持的媒体类型")

    if isinstance(exc, NotAcceptable):
        log.warn("NotAcceptable: %s" % exc)
        return error.ErrorResponse(error.NotAcceptable, "NotAcceptable")

    if isinstance(exc, ParseError):
        log.warn("ParseError: %s" % exc)
        return error.ErrorResponse(error.ParseError, "ParseError")

    if isinstance(exc, Throttled):
        log.warn("Throttled: %s" % exc)
        return error.ErrorResponse(error.Throttled, "Throttled")

    log.error(exc)
    return error.ErrorResponse(error.SYSTEM_ERROR, 'Internal Server Error', status.HTTP_500_INTERNAL_SERVER_ERROR)



# Change exception handler in v2
v2_api_settings = copy(api_settings)
v2_api_settings.EXCEPTION_HANDLER = custom_exception_handler


class APIView(views.APIView):

    def __init__(self):
        self.settings = v2_api_settings
