# -*- coding: utf-8 -*-
from mock import patch
from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from social_oauth.api import sms_send
from social_oauth.sms import SMS_VERIFICATION_SUCCESS
import json

class TestSMS(TestCase):
    '''
    因为要调用云片api真正发短信，测试yunpian_sms_send并没有意义;
    sms_send只要传两个参数都能跑过,个人认为这个单元测试基本没有任何意义,
    因为测试中我们不会真的去调用云片api。
    '''

    def setUp(self):
        self.phone_number = '18600000000'
        self.mock_yunpian_response_value = '{"code":0,"msg":"OK","result":{"count":1,"fee":1,"sid":1794285937}}'
        self.client = Client()
        self.url = reverse('send_sms_validate')

    def _get_response_json_dict(self, response):
        return json.loads(response.content)

    def test_send_sms_validate(self):
        '''
        验证码要有1分钟的时间间隔，单元测试比较快，因此多次发送应该是"验证码发送频率高的提示"
        '''
        with patch('social_oauth.api.yunpian_sms_send') as mock_yunpian_sms_send, patch('social_oauth.sms.SMSValidate.check') as mock_smsvalidate_check:
            mock_yunpian_sms_send.return_value = self.mock_yunpian_response_value
            mock_smsvalidate_check.return_value = SMS_VERIFICATION_SUCCESS
            # 1次
            response = self.client.post(self.url, {'phone_number': self.phone_number})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(self._get_response_json_dict(response)['success'])
            # 2次
            response = self.client.post(self.url, {'phone_number': self.phone_number})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self._get_response_json_dict(response)['success'])
            self.assertEqual(self._get_response_json_dict(response)['messages']['validate'], u"验证码发送频率过高")
            # 3次
            response = self.client.post(self.url, {'phone_number': self.phone_number})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self._get_response_json_dict(response)['success'])
            self.assertEqual(self._get_response_json_dict(response)['messages']['validate'], u"验证码发送频率过高")
            # 4次
            response = self.client.post(self.url, {'phone_number': self.phone_number})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self._get_response_json_dict(response)['success'])
            self.assertEqual(self._get_response_json_dict(response)['messages']["captcha"], u"验证码错误")
            response = self.client.get(reverse('sms_validate_image'))
            # 5次
            response = self.client.post(
                self.url, {
                    'phone_number': self.phone_number,
                    'captcha': self.client.session['sms_verify'],
                })
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self._get_response_json_dict(response)['success'])
            self.assertEqual(self._get_response_json_dict(response)['messages']['validate'], u"验证码发送频率过高")
            # 6次
            response = self.client.post(self.url, {'phone_number': self.phone_number})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self._get_response_json_dict(response)['success'])
            self.assertEqual(self._get_response_json_dict(response)['messages']["captcha"], u"验证码错误")
            # 检查验证码
            self.client.get(reverse('sms_validate_image'))
            response = self.client.post(reverse('check_sms_validate'),
                    {
                        'phone_number': self.phone_number,
                        'captcha': self.client.session['sms_verify'],
                        'validate': 'xxxx',
                    })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(self._get_response_json_dict(response)['success'])
            # 验证成功后第一次
            response = self.client.post(self.url, {'phone_number': self.phone_number})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(self._get_response_json_dict(response)['success'])
            self.assertEqual(self._get_response_json_dict(response)['messages']['validate'], u"验证码发送频率过高")
