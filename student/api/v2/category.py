# -*- coding: utf-8 -*-

import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from api.utils import get_screen_size, get_thumbnail_size
from api.v2.serializer import CategorySerializer, CourseSerializer, CourseWithoutStaffSerializer
from api.v2.views import APIView
from course_meta.models import CourseCategory, CategoryGroup

log = logging.getLogger(__name__)

class CategoriesView(APIView):

    def get(self, request, format=None):
        """ Get the category list. """
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 0)),
            # 'group': request.GET.get('group', 'xuetangx_xuetangx'),  # 默认主站分类 group
        }

        if param['offset'] < 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'androidtv' in user_agent:
            slug = 'tv'
            owner = 'xuetangx'
        else:
            slug = 'xuetangx'
            owner = 'xuetangx'

        cg = CategoryGroup.objects.filter(slug=slug, owner=owner)
        query = CourseCategory.objects.filter(group__in=cg)
        total = query.count()
        if param['limit']:
            categories = query[param['offset']:
                               param['offset'] + param['limit']]
        else:
            categories = query[param['offset']:]

        result = {
            "categories": CategorySerializer(categories, many=True).data,
            "total": total,
        }
        return Response(result)


class CategorieCourseView(APIView):

    def get(self, request, cid, format=None):
        """ Get the courses of current category. """
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
            'show_staffs': int(request.GET.get('show_staffs', 0)),
        }

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='list')

        category = CourseCategory.objects.get(id=cid)
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'androidtv' in user_agent:
            is_tv = True
        else:
            is_tv = False

        if is_tv:
            query = category.course_set.filter((~Q(status=-1)) & (Q(course_type=1)))
        else:
            query = category.course_set.filter(status__gte=0, course_type=0)

        total = query.count()
        courses = query[param['offset']:param['offset'] + param['limit']]

        if param['show_staffs']:
            courses_json = CourseSerializer(thumbnail_size, courses, many=True).data
        else:
            courses_json = CourseWithoutStaffSerializer(thumbnail_size, courses, many=True).data
        result = {
            "courses": courses_json,
            "total": total,
        }
        return Response(result)
