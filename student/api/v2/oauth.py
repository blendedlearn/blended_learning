# -*- coding: utf-8 -*-
import json
import api.v2.error as error
from logging import getLogger

from requests.exceptions import HTTPError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.utils import get_access_token, token_view_check
from api.v2.views import APIView
from django.conf import settings
from provider.oauth2.views import AccessTokenView
from social_auth.exceptions import AuthAlreadyAssociated, NotAllowedToDisconnect
from social_oauth.utils import get_strategy, social_account_bind_status
from social_oauth.views import (_get_or_create_oauth_user, _new_association,
                                _unbind_social)
from track.views import server_track

log = getLogger(__name__)


class OAuthBindView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, provider):
        data = request.DATA
        uid = data.get('uid')
        access_token = data.get('access_token')
        strategy = get_strategy(provider)
        social_response = {
            'access_token': access_token,
            'uid': uid,
            'openid': uid,
            'provider': provider,
        }
        log.info('api.oauth.bind.outer.login\n{}'.format(social_response))
        if provider == 'qq':
            social_response.update({
                'SOCIAL_AUTH_QQ_KEY': settings.SOCIAL_AUTH_MOBILE_QQ_OAUTH_CONSUMER_KEY
            })
        try:
            # 请求三方接口获得用户信息
            detail = strategy.backend.user_data(access_token, response=social_response)
            log.info('api.user.bind.oauth.login.response\n{}'.format(detail))
            if 'errcode' in detail:
                server_track(request, 'api.user.oauth.bind_failure', {
                    'bind_type': 'social_oauth',
                    'provider': provider,
                    'uid': request.user.id,
                    'error': {
                        'msg': u'三方登录失败',
                        'detail': detail,
                    },
                })
                raise error.Error(error.SOCIAL_OAUTH_LOGIN_FAILED, u'三分登陆失败')
        except Exception as ex:
            server_track(request, 'api.user.oauth.bind_failure', {
                'bind_type': 'social_oauth',
                'provider': provider,
                'uid': request.user.id,
                'error': {
                    'msg': ex.__class__.__name__,
                }
            })
            raise error.Error(error.SOCIAL_OAUTH_LOGIN_FAILED, u'三分登陆失败')

        try:
            _new_association(strategy, detail, request.user, created_on='mobile_bind')
            server_track(request, 'api.user.oauth.bind_success', {
                'unbind_type': 'social_oauth',
                'provider': provider,
                'uid': request.user.id
            })
        except AuthAlreadyAssociated as ex:
            server_track(request, 'api.user.oauth.bind_failure', {
                'bind_type': 'social_oauth',
                'provider': provider,
                'uid': request.user.id,
                'error': {
                    'msg': ex.__class__.__name__,
                }
            })
            raise error.Error(error.SOCIAL_OAUTH_AUTH_ALREADY_ASSOCIATED, u'该账号已被其它账号绑定')
        return Response(status=status.HTTP_201_CREATED)


class OAuthUnBindView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, provider):
        try:
            _unbind_social(request.user, provider)
            server_track(request, 'api.user.oauth.unbind_success', {
                'unbind_type': 'social_oauth',
                'provider': provider,
                'uid': request.user.id
            })
        except NotAllowedToDisconnect as ex:
            server_track(request, 'api.user.oauth.unbind_failure', {
                'unbind_type': 'social_oauth',
                'provider': provider,
                'uid': request.user.id,
                'error': {
                    'msg': ex.__class__.__name__,
                }
            })
            raise error.Error(error.SOCIAL_OAUTH_NOT_ALLOWED_TO_DISCONNECT, u'您未绑定过其他联系方式或者{}账号，不能解绑'.format(provider))
        return Response(status=status.HTTP_204_NO_CONTENT)


class OAuthAccountStatus(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        social_status, can_unbind_social_account = social_account_bind_status(request.user)
        result = {
            'can_unbind': can_unbind_social_account,
            'status': social_status
        }
        return Response(result)
