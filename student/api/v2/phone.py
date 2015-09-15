# -*- coding: utf-8 -*-
import json
import logging
import api.v2.error as error
import base64
import time
import random
from string import lowercase, uppercase, digits
from api.v2.views import APIView
from datetime import datetime, timedelta
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from social_oauth.api import sms_send
from pytz import UTC, timezone
from student.models import UserProfile
from util.string_utils import (ALL_NUMBER_RE, USERNAME_RE, string_len, PHONE_NUMBER_RE)
from social_oauth.models import (SMS_OUT_OF_DATE, SMS_TOO_FREQUENTLY,
                                 SMS_VERIFICATION_FAILED,
                                 SMS_VERIFICATION_SUCCESS,
                                 SMS_WAIT_TO_CHECK, SMSValidate,
                                 SMS_SEND_FAILED, SMSValidateCheckFailures,
                                 SMS_RECHECKED)
import base64

def encode(phone_number, uuid):
    timestamp = time.time()
    real_input = '{}#{}#{}'.format(phone_number, uuid, timestamp)
    code = random.choice(lowercase)
    output = []
    for index, s in enumerate(real_input):
        output.append(chr(ord(s)^ord(code)))
        if index % 3 == 0:
            output.append(random.choice(lowercase))
        elif index % 3 == 1:
            output.append(random.choice(uppercase))
        else:
            output.append(random.choice(digits))
    return '{}{}'.format(base64.b64encode(''.join(output)), code)

def decode(s):
    '''
    移动端给的一个解密算法
    成功返回 手机号#uuid#时间戳
    '''
    code, real_input = s[-1], s[:-1]
    try:
        output = base64.b64decode(real_input)
    except Exception:
        return ''
    if (len(output) % 2):
        return ''
    return ''.join([chr(ord(i)^ord(code)) for i in output[::2]])

def check_phone_number(post_vars):
    if 'phone' not in post_vars:
        raise error.Error(error.MISSING_PARAMETER, u'缺少参数phone')

    if 'validate' not in post_vars:
        raise error.Error(error.MISSING_PARAMETER, u'缺少参数validate')

    phone_number = post_vars['phone']
    validate = post_vars['validate']

    if not PHONE_NUMBER_RE.match(phone_number):
        raise error.Error(error.PHONE_NUMBER_FORMAT_ERROR, u'手机号格式错误')


def check_validate_used(post_vars, time_out=60*5):
    '''
    检查一个验证码是否被成功检测过，检测过将状态更新
    '''
    phone_number = post_vars.get('phone')
    validate = post_vars.get('validate')
    validates = SMSValidate.objects.filter(
        status=SMS_VERIFICATION_SUCCESS,
        phone_number=phone_number,
        validate=validate
    ).order_by('-updated_at')
    if not validates.exists():
        raise error.Error(error.SMS_VERIFICATION_FAILED, u'验证码错误')
    now = datetime.now(UTC)
    delta = timedelta(seconds=time_out)
    validates = list(validates)
    for each in validates[1:]:
        each.status = SMS_OUT_OF_DATE
        each.save()
    if now < validates[0].updated_at + delta:
        return validates[0]
    raise error.Error(error.SMS_OUT_OF_DATE, u'验证码已过期')


class SMSValidateView(APIView):

    def post(self, request):
        post_vars = request.DATA
        if 'phone' not in post_vars or not post_vars['phone']:
            raise error.Error(error.MISSING_PARAMETER, u'缺少参数phone')
        phone_number = post_vars['phone']
        if not PHONE_NUMBER_RE.match(phone_number):
            raise error.Error(error.PHONE_NUMBER_FORMAT_ERROR, u'手机号格式错误')
        if 'authtoken' not in post_vars or not post_vars['authtoken']:
            raise error.Error(error.MISSING_PARAMETER, u'缺少参数authtoken')
        authtoken = decode(post_vars['authtoken'])
        tokens = authtoken.split('#')
        if not authtoken or (len(tokens) != 3):
            raise error.Error(error.AUTHTOKEN_FORMAT_ERROR, u'authtoken格式错误')
        t_phone_number, t_uuid, t_timestamp = tokens
        if phone_number != t_phone_number:
            logging.error('api请求手机号:{} token手机号:{}, 可能盗用短信接口'.format(phone_number, t_phone_number))
            raise error.Error(error.AUTHTOKEN_FORMAT_ERROR, u'authtoken错误')
        if SMSValidate.objects.filter(token=authtoken).exists():
            raise error.Error(error.AUTHTOKEN_OUT_OF_DATE, u'authtoken过期')

        if 'check_phone_type' not in post_vars or not post_vars['check_phone_type']:
            # raise error.Error(error.MISSING_PARAMETER, u'缺少参数check_phone_type)  # blocked for another field check_phone_type  check
            pass
        else:
            check_phone_type = post_vars.get('check_phone_type')
            exist = UserProfile.objects.filter(phone_number=phone_number).exists()

            if check_phone_type == '1':  # register
                if exist:
                    raise error.Error(error.PHONE_NUMBER_EXIST, u'该手机已被注册或绑定')
            elif check_phone_type == '2':  # forget
                if not exist:
                    raise error.Error(error.PHONE_NUMBER_DONT_EXIST, u'该手机号尚未注册')
            elif check_phone_type == '3':  # bind
                if exist:
                    raise error.Error(error.PHONE_ALREADY_BIND, u'该手机号已经被绑定过了喔')
            else:  # unsupported type
                raise error.Error(error.INVALID_PARAMETER, u'参数错误:check_phone_type({})'.format(check_phone_type))

        if 'check_phone_type' not in post_vars:  # need to keep it for old app client
            check_phone_registed = post_vars.get('check_phone_registed')
            if check_phone_registed == '1' or check_phone_registed == 'true':
                if UserProfile.objects.filter(phone_number=phone_number).exists():
                    raise error.Error(error.PHONE_NUMBER_EXIST, u'该手机已被注册或绑定')

        sms_list = SMSValidate.objects.filter(status=SMS_WAIT_TO_CHECK, phone_number=phone_number).order_by('-created_at')
        # 防止用户恶意注册
        if sms_list.exists():
            sms_obj = sms_list[0]
            if sms_obj.is_too_frequently():
                raise error.Error(error.SMS_TOO_FREQUENTLY, SMSValidate.STATUS[SMS_TOO_FREQUENTLY])
        obj = SMSValidate.new(phone_number, token=authtoken)
        resp = sms_send(phone_number, obj.validate)
        sms_response = json.loads(resp)
        # 状态码0为成功
        # http://www.yunpian.com/api/retcode.html
        if sms_response['code']:
            raise error.Error(error.SMS_SEND_FAILED, u'验证码发送失败')
        logging.info('api.sms.validate.send phone [{}] result [{}]'.format(phone_number, resp))
        return Response(status=status.HTTP_204_NO_CONTENT)


class SMSValidateConfirmView(APIView):

    def post(self, request, time_out=60*5):
        post_vars = request.DATA
        check_phone_number(post_vars)
        phone_number = request.DATA['phone']
        validate = request.DATA['validate']
        validates = SMSValidate.objects.filter(
            ~Q(status=SMS_OUT_OF_DATE),
            phone_number=phone_number,
            validate=validate
        ).order_by('-updated_at')
        now = datetime.now(UTC)
        delta = timedelta(seconds=time_out)
        validates = list(validates)
        validates_num = len(validates)

        if not validates_num:
            raise error.Error(error.SMS_VERIFICATION_FAILED, u'验证码错误')

        success_validates = []
        for each in validates:
            if each.updated_at and now < each.updated_at + delta:
                if each.status != SMS_VERIFICATION_SUCCESS:
                    each.status = SMS_VERIFICATION_SUCCESS
                    each.save()
                success_validates.append(each)

        success_validates_num = len(success_validates)

        if not success_validates_num:
            raise error.Error(error.SMS_VERIFICATION_FAILED, u'验证码错误')

        return Response(status=status.HTTP_204_NO_CONTENT)
