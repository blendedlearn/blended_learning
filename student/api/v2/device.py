# -*- coding: utf-8 -*-

import logging

from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

import api.v2.error as error
import json
from api.models import DeviceInfo, LogUploadStrategy
from api.v2.views import APIView
from track.views import server_track
import logging


class DeviceView(APIView):

    def post(self, request):
        data = json.loads(request.DATA.get('data', "{}"))
        uuid = data.get('uuid')
        timestamp = data.get('timestamp', '')
        device_info = data.get('deviceInfo', {})
        device, _ = DeviceInfo.objects.get_or_create(uuid=uuid)
        device.uuid = uuid
        device.timestamp = timestamp
        device.raw_data = device_info
        for filed, post_filed in DeviceInfo.DEVICE_INFO_FILED_MAPPER.iteritems():
            setattr(device, filed, device_info.get(post_filed, ''))
        device.save()
        return Response({'success': True}, status.HTTP_200_OK)
