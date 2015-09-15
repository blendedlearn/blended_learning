# -*- coding: utf-8 -*-
import json
import logging
import re

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.validators import (validate_email, validate_slug,
                                    ValidationError)
from django.db.models import Q
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import api.v2.error as error
from api.v2.views import APIView
from util.check_usr_pwd import check_password
from verify_student.models import SoftwareSecurePhotoVerification
from api.v2.phone import check_phone_number, check_validate_used
from django.contrib.auth.models import User
from student.forms import PasswordResetFormNoActive
from student.models import UserProfile
from student.views import (_do_create_account, _change_email_request)
from track.views import server_track
from util.string_utils import (ALL_NUMBER_RE, USERNAME_RE, string_len, PHONE_NUMBER_RE)
from social_oauth.models import (SMS_OUT_OF_DATE, SMS_TOO_FREQUENTLY,
                                 SMS_VERIFICATION_FAILED,
                                 SMS_VERIFICATION_SUCCESS,
                                 SMS_WAIT_TO_CHECK, SMSValidate,
                                 SMS_SEND_FAILED, SMSValidateCheckFailures)


log = logging.getLogger(__name__)

RE_USERNAME_EXIST = re.compile(u".*对应的账户已存在")
RE_EMAIL_EXIST = re.compile(u".*对应的账户已存在")
RE_PHONE_NUMBER_EXIST = re.compile(u"此手机号已被注册")
RE_USERNAME_CANT_ALL_NUMBER = re.compile(u"用户名不能都为数字")

def _register(post_vars, is_active=True, use_phone_number=False,
        use_email=True, request=None):
    ret = _do_create_account(post_vars, is_active,
            use_phone_number=use_phone_number, use_email=use_email,
            request=request)
    # if there was an error then return that
    # 转化为对应错误码
    if isinstance(ret, HttpResponse):
        result = json.loads(ret.content)
        value = result.get('value')
        field = result.get('field')
        err_code = error.REGISTER_FAILED
        if field == 'username':
            if RE_USERNAME_EXIST.match(value):
                err_code = error.USERNAME_EXIST
            elif RE_USERNAME_CANT_ALL_NUMBER(value):
                err_code = error.USERNAME_CANT_ALL_NUMBER
        elif field == 'phone_number':
            if RE_PHONE_NUMBER_EXIST.match(value):
                error_code = error.PHONE_NUMBER_EXIST
        elif field == 'email':
            if RE_EMAIL_EXIST.match(value):
                err_code = error.EMAIL_EXIST
        raise error.Error(err_code, value)
    else:
        return ret

def check_email(post_vars):
    if 'email' not in post_vars:
        raise error.Error(error.MISSING_PARAMETER, u'缺少参数email')

    # Check paremeters
    if len(post_vars['email']) < 2:
        raise error.Error(error.EMAIL_FORMAT_ERROR, _(u'邮箱格式不正确'))

    # Validate email
    try:
        validate_email(post_vars['email'])
    except ValidationError:
        raise error.Error(error.EMAIL_FORMAT_ERROR, _(u'邮箱格式不正确'))


def check_password_for_api(password):
    ret = check_password(password)
    if ret == -1:
        raise error.Error(error.PASSWORD_ILLEGAL, u'您的密码过于简单，请重新输入')
    elif ret == -2:
        raise error.Error(error.PASSWORD_ILLEGAL, u'密码不能包含空格')
    elif ret == -3:
        raise error.Error(error.PASSWORD_ILLEGAL, u'您的密码过于简单，请重新输入')
    elif ret == -4:
        raise error.Error(error.PASSWORD_ILLEGAL, u'密码长度应在6-20个字符之间')


def get_user_info(user):
    profile = user.profile
    bind_password = user.password != '!'
    verification_status = 'approved' if SoftwareSecurePhotoVerification.user_is_verified(user) else 'none'
    return {
        'uid': user.id,
        'username': profile.nickname,
        'name': profile.name,
        'email': user.email,
        'phone_number': profile.phone_number,
        'gender': profile.gender,
        'year_of_birth': profile.year_of_birth,
        'level_of_education': profile.level_of_education,
        'goals': profile.goals,
        'mailing_address': profile.mailing_address,
        'avatar': profile.avatar_url,
        'unique_code': profile.unique_code,
        'bind_password': bind_password,
        'verification_status': verification_status
    }


class UserView(APIView):

    def post(self, request, format=None):
        """ Register a new user. """
        post_vars = request.DATA.copy()
        if 'email' in post_vars:
            register_type = 'email'
        else:
            register_type = 'phone'

        if post_vars.get('register_type', '') == 'auto':
            register_type = 'auto'

        try:
            if 'email' == register_type:
                user, profile, registration = self.create_user_with_email(post_vars, request=request)
            elif 'auto' == register_type:
                user, profile, registration = self.create_tv_user(post_vars, request=request)
            else:  # phone
                user, profile, registration = self.create_user_with_phone(post_vars, request=request)
        except error.Error as ex:
            server_track(request, 'api.user.register_failure', {
                'msg': u'注册失败',
                'register_type': register_type,
                'error': {
                    'msg': ex.err_message,
                    'error_code': ex.err_code,
                },
            })
            raise ex

        result = get_user_info(user)
        response = Response(result, status.HTTP_201_CREATED)
        response['register_type'] = register_type
        server_track(request, 'api.user.register_success', {
            'uid': user.id,
            'username': user.username,
            'register_type': register_type,
        })
        return response

    def check_common_params(self, post_vars):
        required_post_vars = ['username', 'password']
        for k in required_post_vars:
            if k not in post_vars:
                raise error.Error(error.MISSING_PARAMETER, u'缺少参数{}'.format(k))
        # Check paremeters
        for k in required_post_vars:
            if len(post_vars[k]) < 2:
                error_str = {
                    'username': (error.USERNAME_LENGHT_TOO_SHORT, _(u'用户名至少需要2个字符')),
                    'password': (error.PASSWORD_LENGHT_TOO_SHORT, _(u'密码长度不能小于2')),
                }
                raise error.Error(error_str[k][0], error_str[k][1])

        if string_len(post_vars['username']) > 30:
            raise error.Error(error.USERNAME_LENGHT_TOO_LONG, _(u'用户名最多30个字符'))

        if ALL_NUMBER_RE.match(post_vars['username']):
            raise error.Error(error.USERNAME_CANT_ALL_NUMBER, _(u'用户名不能都为数字'))

        if not USERNAME_RE.match(post_vars['username']):
            raise error.Error(error.USERNAME_FORMAT_ERROR, _(u'用户名只能包含中文字符、英文字母、数字、"_"及"-"，不能包含空格'))


    def create_user_with_email(self, post_vars, request=None):
        ''' use email password register
        return user, profile, registration
        '''
        # Confirm we have a properly formed request
        self.check_common_params(post_vars)
        check_email(post_vars)

        if not post_vars.get('name'):
            post_vars['name'] = ''
        return _register(post_vars, request=request)

    def create_tv_user(self, post_vars, request=None):
        ''' use user password register
        return user, profile, registration
        '''
        # Confirm we have a properly formed request
        self.check_common_params(post_vars)

        if not post_vars.get('name'):
            post_vars['name'] = ''
        return _register(post_vars, use_email=False, request=request)

    def create_user_with_phone(self, post_vars, request=None):
        ''' use email password register
        return user, profile, registration
        '''
        # Confirm we have a properly formed request
        self.check_common_params(post_vars)
        check_phone_number(post_vars)
        check_validate_used(post_vars)

        if not post_vars.get('name'):
            post_vars['name'] = ''
        post_vars.setdefault('phone_number', post_vars['phone'])
        return _register(post_vars, use_phone_number=True, request=request)


class PasswordResetView(APIView):

    def reset_password_with_email(self, request):
        form = PasswordResetFormNoActive(request.DATA)
        if form.is_valid():
            form.save(use_https=request.is_secure(),
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      request=request,
                      domain_override=request.get_host())

    def reset_password_with_phone(self, request):
        '''
        只有手机验证验证码成功后才能调用此接口
        '''
        post_vars = request.DATA
        check_phone_number(post_vars)
        if 'password' not in post_vars:
            raise error.Error(error.MISSING_PARAMETER, u'缺少参数password')
        check_validate_used(post_vars)

        phone_number = post_vars['phone']
        password = post_vars['password']

        try:
            profile = UserProfile.objects.get(phone_number=phone_number)
            user = profile.user
            user.set_password(password)
            user.save()
        except UserProfile.DoesNotExist:
            raise error.Error(error.PHONE_NUMBER_DONT_EXIST, u'手机号码不存在')

    def post(self, request, format=None):
        """ Forgot password and send the email. """
        if request.DATA.get('email'):
            try:
                self.reset_password_with_email(request)
                response = Response(status=status.HTTP_204_NO_CONTENT)
                response['reset_type'] = 'email'
                server_track(request, 'api.user.password_reset_success', {
                    'email': request.DATA.get('email'),
                    'reset_type': 'email',
                })
            except error.Error as ex:
                server_track(request, 'api.user.password_reset_failure', {
                    'email': request.DATA.get('email'),
                    'reset_type': 'email',
                    'error': {
                        'msg': ex.err_message,
                        'error_code': ex.err_code,
                    }
                })
                raise ex
        else:
            try:
                self.reset_password_with_phone(request)
                response = Response(status=status.HTTP_204_NO_CONTENT)
                response['reset_type'] = 'phone'
                server_track(request, 'api.user.password_reset_success', {
                    'phone': request.DATA.get('phone'),
                    'reset_type': 'phone',
                })
            except error.Error as ex:
                server_track(request, 'api.user.password_reset_failure', {
                    'phone': request.DATA.get('phone'),
                    'reset_type': 'phone',
                    'error': {
                        'msg': ex.err_message,
                        'error_code': ex.err_code,
                    }
                })
                raise ex
        return response


class PasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request, format=None):
        """ Change user's password. """
        new_password = request.DATA['new_password']
        # Check password
        check_password_for_api(new_password)
        user = authenticate(username=request.user.username,
                            password=request.DATA['password'])
        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        """ Get user profile"""
        result = get_user_info(request.user)
        return Response(result)

    def set_common_profile(self, request, profile):
        param = {
            'name': request.DATA.get('name'),
            'gender': request.DATA.get('gender'),
            'year_of_birth': request.DATA.get('year_of_birth'),
            'level_of_education': request.DATA.get('level_of_education'),
            'goals': request.DATA.get('goals'),
            'mailing_address': request.DATA.get('mailing_address'),
        }

        if param['name']:
            profile.name = param['name']
        if param['gender'] and param['gender'] in UserProfile.GENDER_CHOICES:
            profile.gender = param['gender']
        if param['year_of_birth'] and param['year_of_birth'].isdigit():
            profile.year_of_birth = param['year_of_birth']
        if param['level_of_education'] and param['level_of_education'] in UserProfile.LEVEL_OF_EDUCATION_CHOICES:
            profile.level_of_education = param['level_of_education']
        if param['goals']:
            profile.goals = param['goals']
        if param['mailing_address']:
            profile.mailing_address = param['mailing_address']

        return profile

    def put(self, request, format=None):
        post_vars = request.DATA.copy()
        email = post_vars.get('email')
        phone_number = post_vars.get('phone')
        validate = post_vars.get('validate')
        user = request.user
        if email:
            if not user.email:
                raise error.Error(error.EMAIL_NOT_BIND, u'未绑定邮箱')
            check_email(post_vars)
            post_vars.setdefault('new_email', email)
            response = _change_email_request(request.user, post_vars, need_password=False)
            result = json.loads(response.content)
            success = result.get('success')
            if not success:
                raise error.Error(error.EMAIL_CHANGE_FAILED, result.get('error'))

        profile = user.profile
        profile = self.set_common_profile(request, profile)

        if phone_number:
            if not profile.phone_number:
                raise error.Error(error.PHONE_NOT_BIND, u'未绑定手机号')
            check_phone_number(post_vars)
            check_validate_used(post_vars)
            profile.phone_number = phone_number

        try:
            profile.save()
        except IntegrityError:
            raise error.Error(error.PHONE_NUMBER_EXIST, u'手机号已存在')

        return Response(get_user_info(request.user), status=status.HTTP_202_ACCEPTED)


class UserPhoneView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        post_vars = request.DATA
        check_phone_number(post_vars)
        check_validate_used(post_vars)
        user = request.user
        phone_number = post_vars.get('phone')
        password = post_vars.get('password')
        if password:
            if user.password != '!':
                server_track(request, 'api.user.phone.bind_failure', {
                    'bind_type': 'phone',
                    'provider': '',
                    'uid': request.user.id,
                    'error': {
                        'msg': 'PASSWORD_ALREADY_BIND',
                        'detail': phone_number,
                    }
                })
                raise error.Error(error.PASSWORD_ALREADY_BIND, u'之前已绑定密码')
            user.set_password(password)
        profile = user.profile
        if profile.phone_number:
            server_track(request, 'api.user.phone.bind_failure', {
                'bind_type': 'phone',
                'provider': '',
                'uid': request.user.id,
                'error': {
                    'msg': 'PASSWORD_ALREADY_BIND',
                    'detail': phone_number,
                }
            })
            raise error.Error(error.PASSWORD_ALREADY_BIND, u'该手机已被注册或绑定')
        check_validate_used(post_vars)
        profile.phone_number = phone_number
        try:
            profile.save()
        except IntegrityError:
            server_track(request, 'api.user.phone.bind_failure', {
                'bind_type': 'phone',
                'provider': '',
                'uid': request.user.id,
                'error': {
                    'msg': 'PHONE_NUMBER_EXIST',
                    'detail': phone_number,
                }
            })
            raise error.Error(error.PHONE_NUMBER_EXIST, u'该手机已被注册或绑定')
        user.save()
        server_track(request, 'api.user.phone.bind_success', {
            'bind_type': 'phone',
            'provider': '',
            'uid': user.id,
            'phone_number': phone_number
        })
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserEmailView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        post_vars = request.DATA.copy()
        check_email(post_vars)
        email = post_vars.get('email')
        password = post_vars.get('password')
        users = User.objects.filter(email=email)
        if users.exists():
            server_track(request, 'api.user.email.bind_failure', {
                'bind_type': 'email',
                'provider': '',
                'uid': request.user.id,
                'error': {
                    'msg': 'EMAIL_EXIST',
                    'detail': email,
                }
            })
            raise error.Error(error.EMAIL_EXIST, u'该邮箱已被注册或绑定')
        user = request.user
        if user.email:
            server_track(request, 'api.user.email.bind_failure', {
                'bind_type': 'email',
                'provider': '',
                'uid': request.user.id,
                'error': {
                    'msg': 'EMAIL_ALREADY_BIND',
                    'detail': email,
                }
            })
            raise error.Error(error.EMAIL_ALREADY_BIND, u'该邮箱已被注册或绑定')
        if password:
            if user.password != '!':
                server_track(request, 'api.user.email.bind_failure', {
                    'bind_type': 'email',
                    'provider': '',
                    'uid': request.user.id,
                    'error': {
                        'msg': 'PASSWORD_ALREADY_BIND',
                        'detail': email,
                    }
                })
                raise error.Error(error.PASSWORD_ALREADY_BIND, u'之前已绑定密码')
            user.set_password(password)
        # TODO: 操作前是否需要绑定密码
        post_vars.setdefault('new_email', email)
        response = _change_email_request(user, post_vars, need_password=False)
        result = json.loads(response.content)
        success = result.get('success')
        if not success:
            server_track(request, 'api.user.email.bind_failure', {
                'bind_type': 'email',
                'provider': '',
                'uid': request.user.id,
                'error': {
                    'msg': 'EMAIL_CHANGE_FAILED',
                    'detail': email,
                }
            })
            raise error.Error(error.EMAIL_CHANGE_FAILED, result.get('error'))
        user.email = email
        user.save()

        server_track(request, 'api.user.email.bind_success', {
            'bind_type': 'email',
            'provider': '',
            'uid': user.id,
            'email': email
        })

        return Response(status=status.HTTP_204_NO_CONTENT)

class UserRealMeView(APIView):
    '''
    检查登录用户确实为此用户，而不是其他人
    输入密码确定，返回用户信息
    '''
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        post_vars = request.DATA
        if 'password' not in post_vars:
            raise error.Error(error.MISSING_PARAMETER, u'缺少参数password')
        user = request.user
        password = post_vars['password']
        if not user.check_password(password):
            raise error.Error(error.PASSWORD_ERROR, u'密码错误')
        result = {'uid': user.id}
        return Response(result, status.HTTP_202_ACCEPTED)
