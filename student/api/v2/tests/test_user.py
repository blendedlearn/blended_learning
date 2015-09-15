# coding=utf-8
import json
from mock import patch

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from social_oauth.models import SMSValidate
class UserTest(APITestCase):
    def setUp(self):
        self.user_info_with_phone = {'username': 'lushiyong', 'password': '123456', 'phone': '15901205235'}
        self.user_info_with_email = {'username': 'lushiyong', 'password': '123456', 'email': 'lushiyong@xuetangx.com'}
        self.user_only_email = {'email': 'lushiyong@xuetangx.com'}
        self.user_only_phone = {'phone': '15901205235'}
        self.test_user = User.objects.create_superuser('user_test', 'user_test@user_test.com', 'user_test')

    def test_can_create_user_via_email(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        response = self.client.post(test_url, self.user_info_with_email)
        # print response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_can_create_user_via_phone(self):  # TODO
        test_url = reverse('api:v2_user_register')
        response = self.client.post(test_url, self.user_info_with_phone)
        # print response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # TODO

    def test_user_password_reset_via_email(self):
        test_url = reverse('api:v2_user_password_reset')
        response = self.client.post(test_url, self.user_only_email)
        # print response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_password_reset_via_phone(self):  # TODO
        test_url = reverse('api:v2_user_password_reset')
        response = self.client.post(test_url, self.user_only_phone)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # TODO

    def test_v2_user_change_password(self):
        self.client.login(username='user_test', password='user_test')
        data = {'password': 'user_test', 'new_password': 'user_test'}
        test_url = reverse('api:v2_user_change_password')
        response = self.client.put(test_url, data)
        # print response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_api_oauth2_access_token(self):  # TODO mock client data
        data = {'grant_type': 'password', 'password': '123456', 'client_id': '5ef52de7bbbaa0080de8',
                'client_secret': '9389d21788c4b5e556b1fc7835667fec9917a8df', 'username': 'lushiyong'}
        test_url = '/api/oauth2/access_token'
        response = self.client.post(test_url, data)
        #
        # print '==========='
        # print response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_v2_user_profile_getinfo(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')
        test_url = reverse('api:v2_user_profile')
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual('lushiyong', content.get('username', None))
        self.assertEqual('lushiyong@xuetangx.com', content.get('email', None))

    def test_v2_user_profile_change(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        test_url = reverse('api:v2_user_profile')
        response = self.client.put(test_url, {'gender': 'm'})
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_v2_user_realme(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        test_url = reverse('api:v2_user_pwd_check')
        response = self.client.post(test_url, {'password': '123456'})
        # print response
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        content = json.loads(response.content)
        self.assertEqual(2, content.get('uid', None))

    def test_v2_get_splash_screen(self):
        # TODO
        pass
    def test_v2_get_banners(self):
        # TODO
        pass
    def test_v2_app_upgrade(self):
        # TODO
        pass
    def test_v2_upload_logs(self):
        # TODO
        pass
    def test_v2_get_logs_upload_strategy(self):
        # TODO
        pass
    def test_v2_device_info_upload(self):
        # TODO
        pass
    def test_v2_feedback(self):
        # TODO
        pass
    def test_v2_bind_email(self):
        # TODO
        pass
    def test_v2_bin_phone(self):
        # TODO
        pass

    def test_v2_phone_validate(self):  # TODO 3  register/forget password/bind phonenumber
        # TODO
        pass

    def test_v2_phone_validate_confirm_success(self):
        sms_validate = SMSValidate()
        sms_validate.validate = 123456
        sms_validate.phone_number = 15901205235
        sms_validate.save()

        data = {'phone': '15901205235', 'validate': '123456'}
        test_url = reverse('api:v2_phone_validate_confirm')
        # print test_url
        response = self.client.post(test_url, data)
        # print response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_v2_phone_validate_confirm_fail(self):
        sms_validate = SMSValidate()
        sms_validate.validate = 123456
        sms_validate.phone_number = 15901205235
        sms_validate.save()

        error_data = {'phone': '15901205235', 'validate': '1111111'}
        test_url = reverse('api:v2_phone_validate_confirm')
        # print test_url
        response = self.client.post(test_url, error_data)
        # print response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
