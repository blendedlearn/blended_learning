# -*- coding: utf-8 -*-
import logging
from django.middleware.csrf import CsrfViewMiddleware

log = logging.getLogger(__name__)


class XueTangCsrfViewMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        try:
            if hasattr(request, 'oauth_middleware_token'):  # 如果是移动端传给web的的token， 则跳过csrf验证
                return self._accept(request)
        except Exception, e:
            log.error(e)

        super(XueTangCsrfViewMiddleware, self).process_view(request, callback, callback_args, callback_kwargs)
