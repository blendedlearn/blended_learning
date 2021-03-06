# -*- coding: utf-8 -*-
import json
import urlparse
import logging
import time
from django.http import HttpResponse
from django.conf import settings
from django.http import HttpResponseRedirect, QueryDict
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from . import constants, scope
from student.models import UserProfile
from social_oauth.views import _get_or_create_oauth_user
from social_oauth.utils import get_strategy
from api.models import DeviceInfo, IDsInfo
from api.v2.user import get_user_info
from common.util.string_utils import USERNAME_RE, PHONE_NUMBER_RE
from track.views import server_track
import traceback
import sys


class OAuthError(Exception):
    """
    Exception to throw inside any views defined in :attr:`provider.views`.

    Any :attr:`OAuthError` thrown will be signalled to the API consumer.

    :attr:`OAuthError` expects a dictionary as its first argument outlining the
    type of error that occured.

    :example:

    ::

        raise OAuthError({'error': 'invalid_request'})

    The different types of errors are outlined in :draft:`4.2.2.1` and
    :draft:`5.2`.

    """


class OAuthView(TemplateView):
    """
    Base class for any view dealing with the OAuth flow. This class overrides
    the dispatch method of :attr:`TemplateView` to add no-caching headers to
    every response as outlined in :draft:`5.1`.
    """

    def dispatch(self, request, *args, **kwargs):
        response = super(OAuthView, self).dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['Pragma'] = 'no-cache'
        return response


class Mixin(object):
    """
    Mixin providing common methods required in the OAuth view defined in
    :attr:`provider.views`.
    """
    def get_data(self, request, key='params'):
        """
        Return stored data from the session store.

        :param key: `str` The key under which the data was stored.
        """
        return request.session.get('%s:%s' % (constants.SESSION_KEY, key))

    def cache_data(self, request, data, key='params'):
        """
        Cache data in the session store.

        :param request: :attr:`django.http.HttpRequest`
        :param data: Arbitrary data to store.
        :param key: `str` The key under which to store the data.
        """
        request.session['%s:%s' % (constants.SESSION_KEY, key)] = data

    def clear_data(self, request):
        """
        Clear all OAuth related data from the session store.
        """
        for key in request.session.keys():
            if key.startswith(constants.SESSION_KEY):
                del request.session[key]

    def authenticate(self, request):
        """
        Authenticate a client against all the backends configured in
        :attr:`authentication`.
        """
        for backend in self.authentication:
            client = backend().authenticate(request)
            if client is not None:
                return client
        return None


class Capture(OAuthView, Mixin):
    """
    As stated in section :draft:`3.1.2.5` this view captures all the request
    parameters and redirects to another URL to avoid any leakage of request
    parameters to potentially harmful JavaScripts.

    This application assumes that whatever web-server is used as front-end will
    handle SSL transport.

    If you want strict enforcement of secure communication at application
    level, set :attr:`settings.OAUTH_ENFORCE_SECURE` to ``True``.

    The actual implementation is required to override :meth:`get_redirect_url`.
    """
    template_name = 'provider/authorize.html'

    def get_redirect_url(self, request):
        """
        Return a redirect to a URL where the resource owner (see :draft:`1`)
        authorizes the client (also :draft:`1`).

        :return: :class:`django.http.HttpResponseRedirect`

        """
        raise NotImplementedError

    def handle(self, request, data):
        self.cache_data(request, data)

        if constants.ENFORCE_SECURE and not request.is_secure():
            return self.render_to_response({'error': 'access_denied',
                'error_description': _("A secure connection is required."),
                'next': None},
                status=400)

        return HttpResponseRedirect(self.get_redirect_url(request))

    def get(self, request):
        return self.handle(request, request.GET)

    def post(self, request):
        return self.handle(request, request.POST)


class Authorize(OAuthView, Mixin):
    """
    View to handle the client authorization as outlined in :draft:`4`.
    Implementation must override a set of methods:

    * :attr:`get_redirect_url`
    * :attr:`get_request_form`
    * :attr:`get_authorization_form`
    * :attr:`get_client`
    * :attr:`save_authorization`

    :attr:`Authorize` renders the ``provider/authorize.html`` template to
    display the authorization form.

    On successful authorization, it redirects the user back to the defined
    client callback as defined in :draft:`4.1.2`.

    On authorization fail :attr:`Authorize` displays an error message to the
    user with a modified redirect URL to the callback including the error
    and possibly description of the error as defined in :draft:`4.1.2.1`.
    """
    template_name = 'provider/authorize.html'

    def get_redirect_url(self, request):
        """
        :return: ``str`` - The client URL to display in the template after
            authorization succeeded or failed.
        """
        raise NotImplementedError

    def get_request_form(self, client, data):
        """
        Return a form that is capable of validating the request data captured
        by the :class:`Capture` view.
        The form must accept a keyword argument ``client``.
        """
        raise NotImplementedError

    def get_authorization_form(self, request, client, data, client_data):
        """
        Return a form that is capable of authorizing the client to the resource
        owner.

        :return: :attr:`django.forms.Form`
        """
        raise NotImplementedError

    def get_client(self, client_id):
        """
        Return a client object from a given client identifier. Return ``None``
        if no client is found. An error will be displayed to the resource owner
        and presented to the client upon the final redirect.
        """
        raise NotImplementedError

    def save_authorization(self, request, client, form, client_data):
        """
        Save the authorization that the user granted to the client, involving
        the creation of a time limited authorization code as outlined in
        :draft:`4.1.2`.

        Should return ``None`` in case authorization is not granted.
        Should return a string representing the authorization code grant.

        :return: ``None``, ``str``
        """
        raise NotImplementedError

    def _validate_client(self, request, data):
        """
        :return: ``tuple`` - ``(client or False, data or error)``
        """
        client = self.get_client(data.get('client_id'))

        if client is None:
            raise OAuthError({
                'error': 'unauthorized_client',
                'error_description': _("An unauthorized client tried to access"
                    " your resources.")
            })

        form = self.get_request_form(client, data)

        if not form.is_valid():
            raise OAuthError(form.errors)

        return client, form.cleaned_data

    def error_response(self, request, error, **kwargs):
        """
        Return an error to be displayed to the resource owner if anything goes
        awry. Errors can include invalid clients, authorization denials and
        other edge cases such as a wrong ``redirect_uri`` in the authorization
        request.

        :param request: :attr:`django.http.HttpRequest`
        :param error: ``dict``
            The different types of errors are outlined in :draft:`4.2.2.1`
        """
        ctx = {}
        ctx.update(error)

        # If we got a malicious redirect_uri or client_id, remove all the
        # cached data and tell the resource owner. We will *not* redirect back
        # to the URL.

        if error['error'] in ['redirect_uri', 'unauthorized_client']:
            ctx.update(next='/')
            return self.render_to_response(ctx, **kwargs)

        ctx.update(next=self.get_redirect_url(request))

        return self.render_to_response(ctx, **kwargs)

    def handle(self, request, post_data=None):
        data = self.get_data(request)

        if data is None:
            return self.error_response(request, {
                'error': 'expired_authorization',
                'error_description': _('Authorization session has expired.')})

        try:
            client, data = self._validate_client(request, data)
        except OAuthError, e:
            return self.error_response(request, e.args[0], status=400)

        authorization_form = self.get_authorization_form(request, client,
            post_data, data)


        if not authorization_form.is_bound or not authorization_form.is_valid():
            return self.render_to_response({
                'client': client,
                'form': authorization_form,
                'oauth_data': data, })

        code = self.save_authorization(request, client,
            authorization_form, data)

        self.cache_data(request, data)
        self.cache_data(request, code, "code")
        self.cache_data(request, client, "client")

        return HttpResponseRedirect(self.get_redirect_url(request))

    def get(self, request):
        return self.handle(request, None)

    def post(self, request):
        return self.handle(request, request.POST)


class Redirect(OAuthView, Mixin):
    """
    Redirect the user back to the client with the right query parameters set.
    This can be either parameters indicating success or parameters indicating
    an error.
    """
    def get(self, request):
        data = self.get_data(request)
        code = self.get_data(request, "code")
        error = self.get_data(request, "error")
        client = self.get_data(request, "client")

        redirect_uri = data.get('redirect_uri', None) or client.redirect_uri

        parsed = urlparse.urlparse(redirect_uri)

        query = QueryDict('', mutable=True)

        if 'state' in data:
            query['state'] = data['state']

        if error is not None:
            query.update(error)
        elif code is None:
            query['error'] = 'access_denied'
        else:
            query['code'] = code

        parsed = parsed[:4] + (query.urlencode(), '')

        redirect_uri = urlparse.ParseResult(*parsed).geturl()

        self.clear_data(request)

        return HttpResponseRedirect(redirect_uri)


class AccessToken(OAuthView, Mixin):
    """
    :attr:`AccessToken` handles creation and refreshing of access tokens.

    Implementations must implement a number of methods:

    * :attr:`get_authorization_code_grant`
    * :attr:`get_refresh_token_grant`
    * :attr:`get_password_grant`
    * :attr:`get_access_token`
    * :attr:`create_access_token`
    * :attr:`create_refresh_token`
    * :attr:`invalidate_grant`
    * :attr:`invalidate_access_token`
    * :attr:`invalidate_refresh_token`

    The default implementation supports the grant types defined in
    :attr:`grant_types`.

    According to :draft:`4.4.2` this endpoint too must support secure
    communication. For strict enforcement of secure communication at
    application level set :attr:`settings.OAUTH_ENFORCE_SECURE` to ``True``.

    According to :draft:`3.2` we can only accept POST requests.

    Returns with a status code of *400* in case of errors. *200* in case of
    success.
    """

    authentication = ()
    """
    Authentication backends used to authenticate a particular client.
    """

    grant_types = ['authorization_code', 'refresh_token', 'password', 'social_oauth']
    """
    The default grant types supported by this view.
    """

    def get_authorization_code_grant(self, request, data, client):
        """
        Return the grant associated with this request or an error dict.

        :return: ``tuple`` - ``(True or False, grant or error_dict)``
        """
        raise NotImplementedError

    def get_refresh_token_grant(self, request, data, client):
        """
        Return the refresh token associated with this request or an error dict.

        :return: ``tuple`` - ``(True or False, token or error_dict)``
        """
        raise NotImplementedError

    def get_password_grant(self, request, data, client):
        """
        Return a user associated with this request or an error dict.

        :return: ``tuple`` - ``(True or False, user or error_dict)``
        """
        raise NotImplementedError

    def get_access_token(self, request, user, scope, client):
        """
        Override to handle fetching of an existing access token.

        :return: ``object`` - Access token
        """
        raise NotImplementedError

    def create_access_token(self, request, user, scope, client):
        """
        Override to handle access token creation.

        :return: ``object`` - Access token
        """
        raise NotImplementedError

    def create_refresh_token(self, request, user, scope, access_token, client):
        """
        Override to handle refresh token creation.

        :return: ``object`` - Refresh token
        """
        raise NotImplementedError

    def invalidate_grant(self, grant):
        """
        Override to handle grant invalidation. A grant is invalidated right
        after creating an access token from it.

        :return None:
        """
        raise NotImplementedError

    def invalidate_refresh_token(self, refresh_token):
        """
        Override to handle refresh token invalidation. When requesting a new
        access token from a refresh token, the old one is *always* invalidated.

        :return None:
        """
        raise NotImplementedError

    def invalidate_access_token(self, access_token):
        """
        Override to handle access token invalidation. When a new access token
        is created from a refresh token, the old one is *always* invalidated.

        :return None:
        """
        raise NotImplementedError

    def error_response(self, error, mimetype='application/json', status=400,
            **kwargs):
        """
        Return an error response to the client with default status code of
        *400* stating the error as outlined in :draft:`5.2`.
        """
        request = kwargs.get('request')
        if request:
            del kwargs['request']
        response = HttpResponse(json.dumps(error), mimetype=mimetype,
                status=status, **kwargs)
        if request:
            set_login_response_header(request, response)
            login_type = response.get('login_type', '')
            error_dict = {
                'login_type': login_type,
                'error': error
            }
            error_dict['error'].update({'msg': error.get('error', u'登录失败')})
            server_track(request, 'api.user.login_failure', error)
        return response

    def access_token_response(self, access_token):
        """
        Returns a successful response after creating the access token
        as defined in :draft:`5.1`.
        """
        user = access_token.user
        info = get_user_info(user)
        result = {
            'access_token': access_token.token,
            'expires_in': access_token.get_expire_delta(),
            'refresh_token': access_token.refresh_token.token,
            'scope': ' '.join(scope.names(access_token.scope)),
        }
        result.update(info)
        return HttpResponse(json.dumps(result), mimetype='application/json')

    def authorization_code(self, request, data, client):
        """
        Handle ``grant_type=authorization_code`` requests as defined in
        :draft:`4.1.3`.
        """
        grant = self.get_authorization_code_grant(request, request.POST,
                client)
        if constants.SINGLE_ACCESS_TOKEN:
            at = self.get_access_token(request, grant.user, grant.scope, client)
        else:
            at = self.create_access_token(request, grant.user, grant.scope, client)
            rt = self.create_refresh_token(request, grant.user, grant.scope, at,
                    client)

        self.invalidate_grant(grant)

        return self.access_token_response(at)

    def refresh_token(self, request, data, client):
        """
        Handle ``grant_type=refresh_token`` requests as defined in :draft:`6`.
        """
        rt = self.get_refresh_token_grant(request, data, client)

        self.invalidate_refresh_token(rt)
        self.invalidate_access_token(rt.access_token)

        at = self.create_access_token(request, rt.user, rt.access_token.scope,
                client)
        rt = self.create_refresh_token(request, at.user, at.scope, at, client)

        return self.access_token_response(at)

    def password(self, request, data, client):
        """
        Handle ``grant_type=password`` requests as defined in :draft:`4.3`.
        """

        data = self.get_password_grant(request, data, client)
        user = data.get('user')
        scope = data.get('scope')

        if constants.SINGLE_ACCESS_TOKEN:
            at = self.get_access_token(request, user, scope, client)
        else:
            at = self.create_access_token(request, user, scope, client)
            rt = self.create_refresh_token(request, user, scope, at, client)

        # track user login ip
        # TODO: track in authorization grant typer last login ip in auth_userprofile
        user_profile = UserProfile.objects.get(user=user)
        user_profile.last_login_ip = request.META.get('REMOTE_ADDR', None)
        user_profile.save()

        sid = request.META.get('HTTP_SID')
        uid = user.id
        uuid = request.META.get('HTTP_UUID')
        if uuid:
            device, _ = DeviceInfo.objects.get_or_create(uuid=uuid)
            device.uid = uid
            device.save()
        if sid:
            timestamp = time.time()
            IDsInfo.new(sid, uid, uuid, timestamp)

        response = self.access_token_response(at)
        set_login_response_header(request, response)
        login_type = response.get('login_type', '')
        server_track(request, 'api.user.login_success', {
            'uid': user.id,
            'username': user.username,
            'login_type': login_type,
        })
        return response

    def social_oauth(self, request, data, client):
        """
        Handle ``grant_type=social_oauth`` requests as defined in :draft:`4.3`.
        """

        data = self.get_social_oauth_grant(request, data, client)
        uid = data.get('uid')
        access_token = data.get('access_token')
        provider = data.get('provider')
        scope = data.get('scope')
        strategy = get_strategy(provider)
        social_response = {
            'access_token': access_token,
            'uid': uid,
            'openid': uid,
            'provider': provider,
        }
        logging.info('api.oauth.outer.login\n{}'.format(social_response))
        if provider == 'qq':
            social_response.update({
                'SOCIAL_AUTH_QQ_KEY': settings.SOCIAL_AUTH_MOBILE_QQ_OAUTH_CONSUMER_KEY
            })
        user = _created = detail = None
        try:
            # 请求三方接口获得用户信息
            detail = strategy.backend.user_data(access_token, response=social_response)
            logging.info('api.user.oauth.login.response\n{}'.format(detail))
            if 'errcode' in detail:
                server_track(request, 'api.user.oauth.login_failure', {
                    'login_type': 'social_oauth',
                    'error': {
                        'msg': u'三方登录失败',
                        'detail': detail,
                    },
                })
                return self.error_response({
                    'error': u'三方登录失败',
                    'error_description': u"三方登录失败"
                }, request=request)
        except Exception as ex:
            server_track(request, 'api.user.oauth.login_failure', {
                'login_type': 'social_oauth',
                'error': {
                    'msg': ex.__class__.__name__,
                }
            })
            return self.error_response({
                'error': u'三方登录失败',
                'error_description': u"三方登录失败"
            }, request=request)

        try:
            # 创建用户: TODO: 异常处理
            user, _created = _get_or_create_oauth_user(strategy, detail,
                    request, mobile_client=True, created_on='mobile')
            if _created:
                server_track(request, 'api.user.oauth.register_success', {
                    'uid': user.id,
                    'username': user.username,
                    'provider': strategy.backend.name,
                })
        except Exception as ex:
            if not user and (_created is None):
                server_track(request, 'api.user.oauth.register_failure', {
                    'register_type': 'social_oauth',
                    'error': {
                        'msg': ex.__class__.__name__,
                    },
                })
            return self.error_response({
                'error': u'三方登录失败',
                'error_description': u"三方登录失败"
            }, request=request)

        if constants.SINGLE_ACCESS_TOKEN:
            at = self.get_access_token(request, user, scope, client)
        else:
            at = self.create_access_token(request, user, scope, client)
            rt = self.create_refresh_token(request, user, scope, at, client)

        # track user login ip
        # TODO: track in authorization grant typer last login ip in auth_userprofile
        user_profile = UserProfile.objects.get(user=user)
        user_profile.last_login_ip = request.META.get('REMOTE_ADDR', None)
        user_profile.save()

        sid = request.META.get('HTTP_SID')
        uid = user.id
        uuid = request.META.get('HTTP_UUID')
        if uuid:
            device, _ = DeviceInfo.objects.get_or_create(uuid=uuid)
            device.uid = uid
            device.save()
        if sid:
            timestamp = time.time()
            IDsInfo.new(sid, uid, uuid, timestamp)
        uuid = request.META.get('HTTP_UUID')

        response = self.access_token_response(at)
        set_login_response_header(request, response)
        login_type = response.get('login_type', '')
        server_track(request, 'api.user.oauth.login_success', {
            'uid': user.id,
            'username': user.username,
            'provider': strategy.backend.name,
            'login_type': login_type,
        })
        if _created:
            response['register_type'] = 'social_oauth'
        return response

    def get_handler(self, grant_type):
        """
        Return a function or method that is capable handling the ``grant_type``
        requested by the client or return ``None`` to indicate that this type
        of grant type is not supported, resulting in an error response.
        """
        if grant_type == 'authorization_code':
            return self.authorization_code
        elif grant_type == 'refresh_token':
            return self.refresh_token
        elif grant_type == 'password':
            return self.password
        elif grant_type == 'social_oauth':
            return self.social_oauth
        return None

    def get(self, request):
        """
        As per :draft:`3.2` the token endpoint *only* supports POST requests.
        Returns an error response.
        """
        return self.error_response({
            'error': 'invalid_request',
            'error_description': _("Only POST requests allowed.")}, request=request)

    def post(self, request):
        """
        As per :draft:`3.2` the token endpoint *only* supports POST requests.
        """
        if constants.ENFORCE_SECURE and not request.is_secure():
            return self.error_response({
                'error': 'invalid_request',
                'error_description': _("A secure connection is required.")}, request=request)

        if not 'grant_type' in request.POST:
            return self.error_response({
                'error': 'invalid_request',
                'error_description': _("No 'grant_type' included in the "
                    "request.")}, request=request)

        grant_type = request.POST['grant_type']

        if grant_type not in self.grant_types:
            return self.error_response({'error': 'unsupported_grant_type'}, request=request)

        client = self.authenticate(request)

        if client is None:
            return self.error_response({'error': 'invalid_client'}, request=request)

        handler = self.get_handler(grant_type)

        try:
            return handler(request, request.POST, client)
        except OAuthError, e:
            return self.error_response(e.args[0], request=request)


def set_login_response_header(request, response):
    '''
    通过用户名判断用户登录方式
    '''
    username = request.POST.get('username')
    grant_type = request.POST.get('grant_type')
    if not username or not grant_type:
        response['login_type'] = 'username'
        return response
    if grant_type == 'social_oauth':
        response['login_type'] = 'social_oauth'
        return response
    if PHONE_NUMBER_RE.match(username):
        response['login_type'] = 'phone'
    elif '@' in username:
        response['login_type'] = 'email'
    else:
        response['login_type'] = 'username'
    return response
