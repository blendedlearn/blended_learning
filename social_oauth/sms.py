# -*- coding: utf-8 -*-
import json
import logging

from django.core.context_processors import csrf
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse

from social_oauth.api import sms_send
from social_oauth.models import (SMS_OUT_OF_DATE, SMS_TOO_FREQUENTLY,
                                     SMS_VERIFICATION_FAILED,
                                     SMS_VERIFICATION_SUCCESS,
                                     SMS_WAIT_TO_CHECK, SMSValidate,
                                     SMS_SEND_FAILED, SMSValidateCheckFailures)
from util.json_request import JsonResponse


@require_POST
def send_sms_validate(request):
    '''
    发送短信验证码，当用户连发三次并且验证不通过(或者根本没验证),要求输入验证码
    '''
    phone_number = request.POST.get('phone_number')
    js = {'success': False, 'messages': {}}
    if not phone_number:
        js['messages']['phone_number'] = u'手机号不能为空'
        return JsonResponse(js)

    if SMSValidateCheckFailures.is_phone_locked_out(phone_number):
        captcha = request.POST.get('captcha', '')
        verify = request.session.get('sms_verify', '')
        request.session['sms_verify'] = '!'
        if not captcha or verify.lower() != captcha.lower():
            logging.info(
                "sms captcha image error, session verify: %s, user captcha: %s", verify, captcha)
            js['validation'] = True
            js['sms_validate_image'] = reverse('sms_validate_image')
            js['messages']['captcha'] = u'验证码错误'
            return JsonResponse(js)

    # 防止恶意注册, 次数限制
    SMSValidateCheckFailures.increment_lockout_counter(phone_number)

    sms_list = SMSValidate.objects.filter(status=SMS_WAIT_TO_CHECK, phone_number=phone_number).order_by('-created_at')
    # 防止用户恶意注册
    if sms_list.exists():
        sms_obj = sms_list[0]
        if sms_obj.is_too_frequently():
            js['messages']['validate'] = SMSValidate.STATUS[SMS_TOO_FREQUENTLY]
            return JsonResponse(js)

    obj = SMSValidate.new(phone_number)
    resp = sms_send(phone_number, obj.validate)
    sms_response = json.loads(resp)
    # 状态码0为成功
    # http://www.yunpian.com/api/retcode.html

    if not sms_response['code']:
        js = {'success': True}
    else:
        js['messages']['validate'] = SMSValidate.STATUS[SMS_SEND_FAILED]

    logging.info('sms.validate.send phone [{}] result [{}]'.format(phone_number, resp))
    return JsonResponse(js)


def _check_sms_validate(phone_number, validate):
    '''
    检查验证码是否正确，正确则解除手机号锁定，错误则锁定计数加1
    '''
    js = {'success': False, 'messages': {}}
    status = SMSValidate.check(phone_number, validate)
    js['messages']['validate'] = SMSValidate.STATUS.get(status, u'验证失败')
    if status == SMS_VERIFICATION_SUCCESS:
        js['success'] = True
        SMSValidateCheckFailures.clear_lockout_counter(phone_number)
    else:
        SMSValidateCheckFailures.increment_lockout_counter(phone_number)
        js['sms_validate_image'] = reverse('sms_validate_image')
        js['validation'] = True
    return js


@require_POST
def check_sms_validate(request):
    phone_number = request.POST.get('phone_number')
    validate = request.POST.get('validate')
    js = _check_sms_validate(phone_number, validate)
    return JsonResponse(js)
