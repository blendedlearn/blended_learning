#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import random
import string
import hashlib
import requests
import logging
from django.conf import settings
from django.core import cache

log = logging.getLogger(__name__)

try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache.cache

class Sign:
    def __init__(self, jsapi_ticket, url):
        self.ret = {
            'nonceStr': self.__create_nonce_str(),
            'jsapi_ticket': jsapi_ticket,
            'timestamp': self.__create_timestamp(),
            'url': url
        }

    def __create_nonce_str(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))

    def __create_timestamp(self):
        return int(time.time())

    def sign(self):
        string = '&'.join(['%s=%s' % (key.lower(), self.ret[key]) for key in sorted(self.ret)])
        self.ret['signature'] = hashlib.sha1(string).hexdigest()
        return self.ret

def get_weixin_accesstoken():
    cache_key = 'weixinapp_access_token'
    access_token = cache.get(cache_key)
    if access_token:
        return access_token
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(
        settings.SOCIAL_AUTH_WEIXINAPP_KEY,
        settings.SOCIAL_AUTH_WEIXINAPP_SECRET
    )
    try:
        response = requests.get(url).json()
    except Exception as ex:
        log.info(ex)
        return ''
    access_token = response.get('access_token')
    expires_in = response.get('expires_in')
    if access_token and expires_in:
        expires_in = int(expires_in)
        cache.set(cache_key, access_token, int(expires_in/4.0*3))
        return access_token
    return ''


def get_jsapi_ticket():
    cache_key = 'weixinapp_jsapi_ticket'
    access_token = get_weixin_accesstoken()
    url = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={}&type=jsapi'.format(
            access_token
    )
    try:
        response = requests.get(url).json()
    except Exception as ex:
        log.info(ex)
        return ''
    ticket = response.get('ticket')
    expires_in = response.get('expires_in')
    if ticket:
        expires_in = int(expires_in)
        cache.set(cache_key, ticket, int(expires_in/4.0*3))
        return ticket
    return ''


def get_signed_js_config(url):
    sign = Sign(get_jsapi_ticket(), url)
    return sign.sign()
