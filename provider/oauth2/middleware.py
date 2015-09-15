# -*- coding: utf-8 -*-
import logging
from django.utils.functional import SimpleLazyObject
from rest_framework import HTTP_HEADER_ENCODING, exceptions
from rest_framework.compat import oauth2_provider, provider_now
from django.utils.translation import ugettext_lazy as _

log = logging.getLogger(__name__)


class OauthMiddleware(object):
    def process_request(self, request):
        try:
            user, token = authenticate(request)
            if user is not None:
                request.user = SimpleLazyObject(lambda: user)
                request.oauth_middleware_token = token
        except Exception, e:
            log.warn(e)


def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, type('')):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


def authenticate_credentials(access_token):
    try:
        token = oauth2_provider.models.AccessToken.objects.select_related('user')
        token = token.get(token=access_token, expires__gt=provider_now())
    except oauth2_provider.models.AccessToken.DoesNotExist:
        log.warn('Not exist!!!')
        raise exceptions.AuthenticationFailed(_('Invalid token.'))

    if not token.user.is_active:
        raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

    return (token.user, token)


def authenticate(request):
    auth = get_authorization_header(request).split()

    if not auth or auth[0].lower() != b'bearer':
        return None, None

    if len(auth) == 1:
        msg = _('Invalid token header. No credentials provided.')
        raise exceptions.AuthenticationFailed(msg)
    elif len(auth) > 2:
        msg = _('Invalid token header. Token string should not contain spaces.')
        raise exceptions.AuthenticationFailed(msg)

    try:
        token = auth[1].decode()
    except UnicodeError:
        msg = _('Invalid token header. Token string should not contain invalid characters.')
        raise exceptions.AuthenticationFailed(msg)

    return authenticate_credentials(token)
