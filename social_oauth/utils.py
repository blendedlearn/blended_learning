# -*- coding: utf-8 -*-
import hashlib
import re
import urllib
import logging
from functools import wraps

from django.contrib.auth.models import make_password, User

from social.exceptions import AuthAlreadyAssociated
from social.pipeline.social_auth import associate_user
from social_auth.exceptions import NotAllowedToDisconnect
from social_auth.models import UserSocialAuth
# from social_auth.views import load_strategy
from util.string_utils import ALL_NUMBER_RE, PHONE_NUMBER_RE


PROVIDER_MAPPER = {
    'weibo': {
        'platform': u'微博',
        'name': 'name',
    },
    'qq': {
        'platform': u'qq',
        'name': 'nickname',
    },
    'douban-oauth2': {
        'platform': u'豆瓣',
        'name': 'uid',
    },
    #'douban': u'豆瓣',
    'weixin': {
        'platform': u'微信',
        'name': 'nickname',
    },
    'renren': {
        'platform': u'人人',
        'name': 'name',
    },
    'baidu': {
        'platform': u'百度',
        'name': 'uname',
    },
}


# def get_strategy(provider):
#     '''
#     provider:
#         type: str
#         example: weibo
#     '''
#     return load_strategy(backend=provider)


def get_uid(strategy, detail):
    return strategy.backend.get_user_id(None, detail)


def new_associate_user(strategy, uid, user, extra_data=None, created_on='web'):
    provider = strategy.backend.name
    if UserSocialAuth.objects.filter(user=user, provider=provider).exists():
        raise AuthAlreadyAssociated(strategy.backend)
    if not extra_data:
        extra_data = {}
    result = associate_user(strategy, uid, user=user)
    sc_user = result['social']
    if sc_user:
        sc_user.extra_data = extra_data
        sc_user.created_on = created_on
        if provider == 'weixin':
            sc_user.weixin_unionid = extra_data['unionid']
        sc_user.save()
    return sc_user


def get_gravatar_url(email, default_avatar=None, use_404=False, size=100):
    '''
    get avatar from gravatar

    doc: https://en.gravatar.com/site/implement/images/
    code: https://en.gravatar.com/site/implement/images/python/

    When you include a default image, Gravatar will automatically serve up that image if there is no image associated with the requested email hash. There are a few conditions which must be met for default image URL:

    MUST be publicly available (e.g. cannot be on an intranet, on a local development machine, behind HTTP Auth or some other firewall etc). Default images are passed through a security scan to avoid malicious content.
    MUST be accessible via HTTP or HTTPS on the standard ports, 80 and 443, respectively.
    MUST have a recognizable image extension (jpg, jpeg, gif, png)
    MUST NOT include a querystring (if it does, it will be ignored)

    Secure Requests
    If you're displaying Gravatars on a page that is being served over SSL
    (e.g. the page URL starts with HTTPS), then you'll want to serve your
    Gravatars via SSL as well, otherwise you'll get annoying security warnings
    in most browsers. To do this, simply change the URL for your Gravatars so
    that is starts with:

        https://secure.gravatar.com/...
    '''
    data = {}
    if default_avatar and default_avatar.startswith('http'):
        data['d'] = default_avatar if not use_404 else '404'
    data['s'] = str(size)
    gravatar_url = "https://secure.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode(data)
    return gravatar_url


NICKNAME_REPLACE_RE = re.compile(r'[@]')


def get_validate_nickname(name):
    '''
    oauth的昵称处理,@替换为_,电话号码形式的加X
    '''
    nickname = re.sub(NICKNAME_REPLACE_RE, '_', name).strip()
    if ALL_NUMBER_RE.match(nickname):
        nickname = '{}X'.format(nickname)
    return nickname


def get_oauth_account_username(usersocialauth):

    return usersocialauth


def check_can_unbind_social_account(user):
    # 用户能否解绑三方代码
    if user.password == make_password(None):
        if UserSocialAuth.objects.filter(user=user).count() == 1:
            raise NotAllowedToDisconnect(u'只有一个三方账号，不能解绑')
    return True


def social_account_bind_status(user):
    social_accounts = UserSocialAuth.objects.filter(user=user)
    status = {}
    for provider in PROVIDER_MAPPER:
        status[provider] = {
            'bind': False,
            'name': '',
        }

    for sa in social_accounts:
        try:
            provider = sa.provider
            provider_status = status[provider]
            provider_status['bind'] = True
            provider_status['name'] = sa.extra_data.get(
                PROVIDER_MAPPER[provider]['name'],
                u'{}平台账号'.format(provider)
            )
        except KeyError as ex:
            logging.error(ex)

    # 用户是否可以解绑三方账号
    # 逻辑：如果没有邮箱，并且只有一个三方账号，不可解绑
    # 用户没有邮箱，没有手机号并且三方账号只有1个
    can_unbind = True
    if not user.email and not user.profile.phone_number and social_accounts.count() <= 1:
        can_unbind = False

    return (status, can_unbind)


def clean_session(field):
    def _clean(func):
        @wraps(func)
        def _wrap(*args, **kwargs):
            request = args[0]
            for f in field:
                request.session[f] = ''
            response = func(*args, **kwargs)
            return response
        return _wrap
    return _clean


def clean_cookie(field):
    def _clean(func):
        @wraps(func)
        def _wrap(*args, **kwargs):
            response = func(*args, **kwargs)
            for f in field:
                response.set_cookie(f, '')
            return response
        return _wrap
    return _clean
