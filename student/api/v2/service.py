# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.core import cache
from pytz import UTC
from rest_framework import status
from rest_framework.response import Response

from api.models import Banner, SplashScreen, AppVersion
from api.v2.serializer import BannerSerializer, SplashScreenSerializer, VersionSerializer
from api.v2.views import APIView


try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache.cache

class BannerView(APIView):
    def get(self, request, format=None):
        belong_str = request.GET.get('belong', 'mobile')
        channel_str = request.GET.get('channel', 'all')
        if 'xiaomi' in channel_str.lower():
            channel_str = 'xiaomi'
        cache_key = 'api.v2.banners.list.{}.{}'.format(belong_str, channel_str)

        cache_result = cache.get(cache_key)
        if cache_result:
            return Response(cache_result)

        """ Get the banner objects. """
        banners = Banner.objects.filter(is_active=True, belong=belong_str,
                                        channel__in=['all', channel_str]).order_by('order')
        result = {
            "banners": BannerSerializer(banners, many=True).data
        }

        cache.set(cache_key, result, 60 * 60)
        return Response(result)


class SplashSreenView(APIView):

    def get(self, request, format=None):
        """ Get the splash screnn image and its activate time. """
        width = int(request.GET.get('width', 0))
        height = int(request.GET.get('height', 0))
        now = datetime.now(UTC)
        screens = SplashScreen.objects.filter(is_active=True, start__lte=now, end__gt=now)
        if not screens:
            return Response({})
        # 根据宽高按照图片宽高比的优先顺序来筛图
        radio = float(width) / height if height else 0
        optimun_screens = {}
        for screen in screens:
            exist = optimun_screens.get(screen.screen_id)
            if not exist:
                optimun_screens[screen.screen_id] = screen
            else:
                screen_radio = float(screen.width) / screen.height if screen.height else 0
                exist_radio = float(exist.width) / exist.height if exist.height else 0
                if screen_radio and exist_radio:
                    if abs(screen_radio - radio) < abs(exist_radio - radio):
                        optimun_screens[screen.screen_id] = screen
        screen = optimun_screens.values()
        if not screen:
            return Response({})
        result = SplashScreenSerializer(screen[0]).data
        return Response(result)


class UpgradeView(APIView):

    def get(self, request, platform, format=None):
        try:
            version = AppVersion.objects.filter(platform=platform).order_by('-release_date')[0]
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        result = VersionSerializer(version).data
        return Response(result)


class FeedbackView(APIView):

    def post(self, request, format=None):
        """ Post the feedback content and user's information. """
        param = {
            'content': request.DATA['content'],
            'contact': request.DATA['contact'],
            'log': request.DATA.get('log'),
        }

        subject = 'Feedback from API v2'
        message = "User: %s\nUserAgent: %s\nContact: %s\nContent: %s\nLog: %s\n" % (
            request.user, request.META.get('HTTP_USER_AGENT', ''), param['contact'], param['content'], param['log'])

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [settings.API_FEEDBACK_EMAIL], fail_silently=True)
        return Response(status=status.HTTP_201_CREATED)

class HeartbeatView(APIView):
    def get(self, request, format=None):
        # url(r'^heartbeat/?$', service.HeartbeatView.as_view(), name='v2_heartbeat'),
        return Response(status=status.HTTP_200_OK)
