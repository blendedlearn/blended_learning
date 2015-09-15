# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from rest_framework import exceptions
from rest_framework.compat import oauth2_provider, provider_now
from rest_framework.authentication import OAuth2Authentication as RFOAuth2Authentication

log = logging.getLogger(__name__)

class OAuth2Authentication(RFOAuth2Authentication):
    '''
    保持主站一致，未激活用户可以做和激活用户一样的事情
    '''

    def authenticate_credentials(self, request, access_token):
        """
        Authenticate the request, given the access token.
        """
        try:
            try:
                if hasattr(request, 'oauth_middleware_token'):
                    return (request.oauth_middleware_token.user, request.oauth_middleware_token)
            except Exception, e:
                log.error(e)

            token = oauth2_provider.models.AccessToken.objects.select_related('user')
            # provider_now switches to timezone aware datetime when
            # the oauth2_provider version supports to it.
            token = token.get(token=access_token, expires__gt=provider_now())
        except oauth2_provider.models.AccessToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        user = token.user

        # 这里是与rest_framework不同的地方，不检查是否激活
        #if not user.is_active:
            #msg = 'User inactive or deleted: %s' % user.username
            #raise exceptions.AuthenticationFailed(msg)

        return (user, token)
