# -*- coding: utf-8 -*-
import requests


YUNPIAN_KEY = '3c452be378b13a89c017ff92ebb30808'


def yunpian_sms_send(phone_number, content, timeout=3, verify=False):
    '''
    doc: http://www.yunpian.com/api/sms.html
    '''
    data = {
        "apikey": YUNPIAN_KEY,
        "mobile": phone_number,
        "text": content,
    }
    resp = requests.post(
        "http://yunpian.com/v1/sms/send.json",
        data,
        timeout=timeout,
        verify=verify
    )
    return resp.content


def sms_send(phone_number, code):
    content = u'您的验证码是{}。如非本人操作，请忽略本短信。【学堂在线】' .format(code)
    return yunpian_sms_send(phone_number, content)
