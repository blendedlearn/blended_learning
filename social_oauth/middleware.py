# -*- coding: utf-8 -*-

import logging

from django.http import HttpResponse

from edxmako.shortcuts import render_to_response
from social_auth.exceptions import (AuthAlreadyAssociated, AuthException,
                                    NotAllowedToDisconnect,
                                    SocialAuthBaseException)
from edxmako.shortcuts import render_to_response
from requests.exceptions import RequestException
from social_oauth.utils import PROVIDER_MAPPER
from util.validators import track_log

log = logging.getLogger(__name__)

class SocialOauthExceptionMiddleware(object):

    def process_exception(self, request, exception):
        if isinstance(exception, AuthAlreadyAssociated):
            return self.handler_AuthAlreadyAssociated(request, exception)
        if isinstance(exception, NotAllowedToDisconnect):
            return self.handler_NotAllowedToDisconnect(request, exception)
        if isinstance(exception, (AuthException, SocialAuthBaseException)):
            return self.handler_AuthException(request, exception)
        # 异常抓的太大 RequestException丢出去
        #if isinstance(exception, (RequestException,)):
            ## add request exception log
            #log.error("RequestException:" + exception.message)
            #return self.handler_RequestException(request, exception)

    def handler_AuthAlreadyAssociated(self, request, exception):
        context = {}
        provider = PROVIDER_MAPPER.get(exception.backend.name, {}).get('platform', u'三方')
        msg = u'{provider}账号绑定失败'.format(provider=provider)
        reason = u'此{provider}账号已绑定过其他学堂账号，或者此学堂账号已经绑定过其他{provider}账号'.format(provider=provider)
        context['failed_title'] = msg
        context['failed_content'] = reason
        track_log(request, 'oauth.user.login_failure', {
            'success': False,
            'field': 'duplicate.{}'.format(provider),
            'context': context,
        })
        return render_to_response('xuetangx/oauth/failed.html', context)

    def handler_NotAllowedToDisconnect(self, request, exception):
        context = {}
        msg = u'不能解绑此账号'
        long_message = u'您只绑定过一个三方账号，并且未绑定过邮箱，不能解绑'
        context['failed_title'] = msg
        context['failed_content'] = long_message
        return render_to_response('xuetangx/oauth/failed.html', context)

    def handler_AuthException(self, request, exception):
        context = {}
        msg = u'账号登陆失败'
        long_message = u'登陆失败，请稍后重试'
        context['failed_title'] = msg
        context['failed_content'] = long_message
        context['retry_url'] = '/dashboard'
        context['retry_content'] = u'使用邮箱密码登陆'
        provider = PROVIDER_MAPPER.get(exception.backend.name, {}).get('platform', u'三方')
        track_log(request, 'oauth.user.login_failure', {
            'success': False,
            'field': 'incorrect.{}'.format(provider),
            'context': context,
        })
        return render_to_response('xuetangx/oauth/failed.html', context)

    def handler_RequestException(self, request, exception):
        context = {}
        msg = u'账号登陆失败'
        long_message = u'登陆失败，请稍后重试。'
        context['retry_url'] = ''
        context['failed_title'] = msg
        context['failed_content'] = long_message
        track_log(request, 'oauth.user.login_failure', {
            'success': False,
            'field': 'incorrect.{}'.format("RequestException"),
            'context': context,
        })
        return render_to_response('xuetangx/oauth/failed.html', context)
