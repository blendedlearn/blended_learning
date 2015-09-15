# -*- coding: utf-8 -*-
from string import strip
from django.core import cache
from rest_framework.response import Response
from rest_framework import status

from track.views import server_track
from api.models import Wisdom
from api.v2.serializer import WisdomSerializer
from api.v2.views import APIView


try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache.cache

class WisdomsView(APIView):
    def get(self, request, format=None):
        cache_key = 'api.v2.wisdoms.list'

        cache_result = None
        if cache_result:
            return Response(cache_result)

        """ Get the wisdom objects. """
        wisdoms = Wisdom.objects.filter(enabled=True).order_by('-id')
        result = {
            "wisdoms": WisdomSerializer(wisdoms, many=True).data
        }

        cache.set(cache_key, result, 60 * 60)
        return Response(result)


class SimpleLogView(APIView):
    def post(self, request, format=None):
        #  url(r'^s_log/?$', tv.SimpleLogView.as_view(), name='v2_simple_log')

        log_content = request.DATA['log_content']

        log_arrays = log_content.split('\n')
        for log_content in log_arrays:
            s_content = strip(log_content)
            if s_content:
                server_track(request, 'api.user.simple_log', {
                    'uid': request.user.id,
                    'uuid': request.META.get('HTTP_UUID'),
                    'sid': request.META.get('HTTP_SID'),
                    'log_content': s_content,
                    'log_content_format': 'json',
                })

        return Response(status=status.HTTP_201_CREATED)
