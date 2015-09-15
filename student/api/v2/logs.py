# -*- coding: utf-8 -*-
import json
from gzip import GzipFile
from StringIO import StringIO
from zipfile import ZipFile
import logging
import uuid
import os

from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone

import api.v2.error as error
from api.models import LogUploadStrategy
from api.utils import cache_response
from api.v2.serializer import LogUploadStrategySerializer
from api.v2.views import APIView
from track.views import server_track

log = logging.getLogger(__name__)

LOG_BASE_ROOT = settings.MOBILE_LOG_ROOT
try:
    if not os.path.exists(LOG_BASE_ROOT):
        os.mkdir(LOG_BASE_ROOT)
except Exception, e:
    log.error(e)

def extract_zip(unextract_file):
    _zipfile = ZipFile(unextract_file)
    namelist = _zipfile.namelist()
    for name in namelist:
        yield StringIO(_zipfile.read(name))


class LogsView(APIView):

    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        now = timezone.now().strftime('%Y%m%d')
        log_root = os.path.join(LOG_BASE_ROOT, now)
        if not os.path.exists(log_root):
            os.mkdir(log_root)
        uid = request.user.id
        platform = None
        http_uuid = request.META.get('HTTP_UUID')
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'ios' in user_agent:
            platform = 'ios'
        elif 'android' in user_agent:
            platform = 'android'

        log_path = os.path.join(log_root, '{}_{}_{}_{}.zip'.format(http_uuid,
            uid, platform, uuid.uuid4().hex[:10]))
        with open(log_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        server_track(request, 'api.user.upload_log', {
            'uid': uid,
            'uuid': http_uuid,
            'sid': request.META.get('HTTP_SID'),
            'log_path': log_path,
        })
        return Response({'success': True}, status.HTTP_200_OK)


class LogUploadStrategyView(APIView):

    @cache_response(60 * 5)
    def get(self, request, device):
        # 查询策略为enabled 并且最近updated_at的策略
        strategies = LogUploadStrategy.objects.filter(enabled=True, device=device).order_by('-updated_at')
        if not strategies.exists():
            raise error.Error(error.SYSTEM_ERROR)
        strategy = strategies[0]
        seri = LogUploadStrategySerializer(strategy)
        return Response(seri.data)
