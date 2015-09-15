#coding:utf-8
# author:duoduo3369@gmail.com  https://github.com/duoduo369
"""
Baidu OAuth2 backend, docs at:
"""
from social.backends.oauth import BaseOAuth2


class BaiduOAuth2(BaseOAuth2):
    """Baidu (of sina) OAuth authentication backend"""
    name = 'baidu'
    ID_KEY = 'userid'
    AUTHORIZATION_URL = 'http://openapi.baidu.com/oauth/2.0/authorize'
    ACCESS_TOKEN_URL = 'https://openapi.baidu.com/oauth/2.0/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False
    EXTRA_DATA = [
        ('username', 'username'),
    ]

    def get_user_details(self, response):
        """Return user details from Baidu. API URL is:
        https://openapi.baidu.com/rest/2.0/passport/users/getInfo
        """
        if self.setting('DOMAIN_AS_USERNAME'):
            username = response.get('domain', '')
        else:
            username = response.get('uname', '')
        return {'username': username,}

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json('https://openapi.baidu.com/rest/2.0/passport/users/getInfo',params={'access_token': access_token})

    def extra_data(self, user, uid, response, details):
        data = super(BaiduOAuth2, self).extra_data(user, uid, response, details)
        portrait = response.get('portrait', None)
        profile_image_url = None if not portrait else 'http://tb.himg.baidu.com/sys/portrait/item/{}'.format(portrait)
        data['profile_image_url'] = profile_image_url
        return data
