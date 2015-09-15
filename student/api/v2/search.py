# -*- coding: utf-8 -*-
from api.models import HotKeyword
from api.utils import search, new_search, get_screen_size, get_thumbnail_size
from api.v2.serializer import CourseSerializer, CaptionSerializer
from api.v2.views import APIView
from course_meta.models import Course
from course_modes.models import CourseMode
from pytz import UTC
from rest_framework.response import Response


class SearchCourseView(APIView):

    def get(self, request, format=None):
        """ Search for courses """
        # Get all the params and set default value
        param = {
            'keyword': request.GET['keyword'],
            'type': request.GET.get('type', 'course'),
            'course_id': request.GET.get('course_id'),
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
        }

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='list')

        # 关键字
        course_list, total = new_search(param['keyword'], _type=param['type'], limit=param['limit'],
                                        offset=param['offset'])

        result = {
            "courses": CourseSerializer(thumbnail_size, course_list, many=True).data,
            "total": total,
        }
        return Response(result)


class SearchHotView(APIView):

    def get(self, request, format=None):
        """ Get the hot search keywords """
        keywords = [hk.keyword for hk in HotKeyword.objects.all()[0:8]]
        result = {
            "keywords": keywords
        }
        return Response(result)
