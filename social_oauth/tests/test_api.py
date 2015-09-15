# -*- coding: utf-8 -*-
from mock import patch
from django.test import TestCase
from django.core.urlresolvers import reverse
from social_oauth.api import sms_send

class TestApi(TestCase):
    '''
    因为要调用云片api真正发短信，测试yunpian_sms_send并没有意义;
    sms_send只要传两个参数都能跑过,个人认为这个单元测试基本没有任何意义,
    因为测试中我们不会真的去调用云片api。
    '''

    def setUp(self):
        self.phone_number = '18600000000'
        self.code = '100000'
        self.mock_yunpian_response_value = '{"code":0,"msg":"OK","result":{"count":1,"fee":1,"sid":1794285937}}'

    def test_sms_send(self):
        with patch('social_oauth.api.yunpian_sms_send') as mock_yunpian_sms_send:
            mock_yunpian_sms_send.return_value = self.mock_yunpian_response_value
            response = sms_send(self.phone_number, self.code)
            self.assertEqual(response, self.mock_yunpian_response_value)
