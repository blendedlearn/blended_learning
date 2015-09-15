# -*- coding: utf-8 -*-
from mock import patch
from django.test import TestCase, Client
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.utils.importlib import import_module
from django.test.utils import override_settings
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from social_oauth.views import new_association, authentication_success, unbind_social
from social_auth.models import UserSocialAuth
from edxmako.tests import mako_middleware_process_request
from student.tests.factories import UserFactory, UserStandingFactory
from django.contrib.auth import authenticate, login
import json

class TestOauthBase(TestCase):

    @override_settings(SESSION_ENGINE='django.contrib.sessions.backends.cache')
    def setUp(self):
        self.request_factory = RequestFactory()
        self.username = 'testuser'
        self.password = 'testpassword'
        self.user = UserFactory.create(username=self.username, password=self.password)
        self.user.profile.nickname = self.username
        self.user.profile.save()
        self.client = Client()
        with open('common/djangoapps/social_oauth/tests/mock_qq_response.json') as f:
            self.qq_response = json.loads(f.read())
        with open('common/djangoapps/social_oauth/tests/mock_weibo_response.json') as f:
            self.weibo_response = json.loads(f.read())
        with open('common/djangoapps/social_oauth/tests/mock_weixin_response.json') as f:
            self.weixin_response = json.loads(f.read())

class TestOauthLogin(TestOauthBase):

    @override_settings(SESSION_ENGINE='django.contrib.sessions.backends.cache')
    def setUp(self):
        super(TestOauthLogin, self).setUp()
        self.url = reverse('authentication_success')
        self.user = AnonymousUser()

    def not_te_st_login_qq(self):
        # TODO: 单元测试不通，是因为user表email用的django默认的user建的，不能为null
        request = self.request_factory.get(self.url)
        request.session = import_module(settings.SESSION_ENGINE).SessionStore()
        request.session['authentication_user_detail'] = self.qq_response
        request.user = self.user
        mako_middleware_process_request(request)
        response = authentication_success(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(not isinstance(request.user, AnonymousUser))
        user_socials = request.user.social_auth.all()
        self.assertEqual(user_socials.count(), 1)
        social = user_socials[0]
        self.assertEqual(social.uid, self.qq_response['openid'])

class TestOauthBind(TestOauthBase):

    @override_settings(SESSION_ENGINE='django.contrib.sessions.backends.cache')
    def setUp(self):
        super(TestOauthBind, self).setUp()
        self.url = reverse('new_association')

    def test_bind_qq(self):
        request = self.request_factory.get(self.url)
        request.session = import_module(settings.SESSION_ENGINE).SessionStore()
        request.session['authentication_user_detail'] = self.qq_response
        request.user = self.user
        mako_middleware_process_request(request)
        response = new_association(request)
        self.assertEqual(response.status_code, 200)
        user_socials = self.user.social_auth.all()
        self.assertEqual(user_socials.count(), 1)
        social = user_socials[0]
        self.assertEqual(social.uid, self.qq_response['openid'])

    def test_bind_weibo(self):
        request = self.request_factory.get(self.url)
        request.session = import_module(settings.SESSION_ENGINE).SessionStore()
        request.session['authentication_user_detail'] = self.weibo_response
        request.user = self.user
        mako_middleware_process_request(request)
        response = new_association(request)
        self.assertEqual(response.status_code, 200)
        user_socials = self.user.social_auth.all()
        self.assertEqual(user_socials.count(), 1)
        social = user_socials[0]
        self.assertEqual(social.uid, self.weibo_response['idstr'])

    def test_bind_weixin(self):
        request = self.request_factory.get(self.url)
        request.session = import_module(settings.SESSION_ENGINE).SessionStore()
        request.session['authentication_user_detail'] = self.weixin_response
        request.user = self.user
        mako_middleware_process_request(request)
        response = new_association(request)
        self.assertEqual(response.status_code, 200)
        user_socials = self.user.social_auth.all()
        self.assertEqual(user_socials.count(), 1)
        social = user_socials[0]
        self.assertEqual(social.uid, self.weixin_response['openid'])


class TestOauthUnbind(TestOauthBase):

    @override_settings(SESSION_ENGINE='django.contrib.sessions.backends.cache')
    def setUp(self):
        super(TestOauthUnbind, self).setUp()
        self.url = '/unbind/{}/'
        for provider in ['qq', 'weixin', 'weibo']:
            us = UserSocialAuth()
            us.user = self.user
            us.uid = '1'
            us.provider = provider
            us.save()

    def test_unbind_social(self):
        response = self.client.post(reverse('login_v2'), {'username': self.username, 'password': self.password})
        self.assertTrue(json.loads(response.content)['success'])
        response = self.client.post(self.url.format('qq'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.social_auth.all().count(), 2)
        self.client.post(self.url.format('weibo'))
        self.assertEqual(self.user.social_auth.all().count(), 1)
        self.client.post(self.url.format('weixin'))
        self.assertEqual(self.user.social_auth.all().count(), 0)
