# -*- coding: utf-8 -*-

from collections import namedtuple
from django.core.cache import cache
from student.models import CourseEnrollment
from functools import wraps
import json
import urllib
import urllib2
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.utils.translation import ugettext as _
from microsite_configuration import microsite
from provider import constants
from provider.oauth2.views import AccessTokenView
from student.models import CourseEnrollment
from course_modes.models import CourseMode
from course_meta.models import Course, CourseCategory
from copy import deepcopy
from datetime import datetime
from django.utils.timezone import UTC
from common.djangoapps.searchservice.searching import search_all_course_id
from track.views import _get_request_header


def search(request, keyword, _type=None):
    try:
        url = "http://%s:%s/%s" % (settings.SEARCH_HOST,
                                   settings.SEARCH_PORT,
                                   urllib.quote(keyword.encode('utf-8')))
        if _type:
            url = "%s?type=%s" % (url, _type)
        httpres = urllib2.urlopen(url.encode('utf-8'))
        res = json.load(httpres)

        result = []
        for doc in res:
            if doc['type'] == _type:
                doc['course_id'] = "%s/%s/%s" % (
                    doc['id']['org'], doc['id']['course'], doc['id']['names']['course'])
                result.append(doc)
        return result
    except:
        return []


def new_search(query, org='', _type=None, cid=0, limit=10, offset=0, started='false', hasTA='false', exclude_ids=[]):
    parameters = {
        'query': query,
        'org': org,
        'cid': cid,
        'limit': limit,
        'offset': offset,
        'started': cmp(started, 'true') == 0,
        'hasTA': cmp(hasTA, 'true') == 0,
        'exclude_ids': exclude_ids,
        '_type': _type,
    }

    search_res = {}
    if parameters['cid']:
        # Get course query by category id
        queryResult = CourseCategory.objects.get(
            id=parameters['cid']).course_set
    elif parameters['query']:
        # Get course query by search api
        course_id_dict = search_all_course_id(parameters['query'])
        queryResult = Course.objects.filter(course_id__in=course_id_dict.keys())
    elif parameters['org']:
        if cmp(parameters['org'], 'edx') == 0:
            queryResult = Course.objects.filter(owner='edX')
        else:
            queryResult = Course.objects.filter(org=parameters['org'])
    else:
        # Get all the courses
        queryResult = Course.objects

    if parameters['started']:
        queryResult = queryResult.filter(serialized__gt=0)

    if parameters['hasTA']:
        now = datetime.now(UTC())
        queryResult = queryResult.filter(owner='xuetangX').filter(
            start__lt=now).filter(end__gt=now)

    if parameters['_type'] == 'recent_course':
        recent_time = datetime.now(UTC()) - timedelta(days=90)
        queryResult = queryResult.filter(start__gt=recent_time)

    # Filter and order by status
    visible_owner = microsite.get_visible_owner()
    verified_courses_ids = CourseMode.get_verified_option_courses()
    queryResult = queryResult.filter(status__gte=0, owner__in=visible_owner, course_type=0).exclude(
        course_id__in=verified_courses_ids).order_by('-status', '-id')

    total_length = queryResult.count()
    courses = sorted(queryResult, key=lambda x: course_id_dict.get(x.course_id, 0))[
              parameters['offset']:parameters['offset'] + parameters['limit']]

    return courses, total_length


def exclude_vpc_and_selfpaced_enrollments(user):
    enrollments = CourseEnrollment.objects.filter(user=user, is_active=True)

    def _exclude_vpc_and_selfpaced(enrollment):
        return Course.objects.filter(
            course_id=enrollment.course_id, owner__in=microsite.get_visible_owner(), course_type=0).exists()

    return filter(_exclude_vpc_and_selfpaced, enrollments)

def token_view_check(token_view, request):
    if constants.ENFORCE_SECURE and not request.is_secure():
        return token_view.error_response({
            'error': 'invalid_request',
            'error_description': _("A secure connection is required.")})

    if not 'grant_type' in request.POST:
        return token_view.error_response({
            'error': 'invalid_request',
            'error_description': _("No 'grant_type' included in the "
                "request.")})

    grant_type = request.POST['grant_type']

    if grant_type not in token_view.grant_types:
        return token_view.error_response({'error': 'unsupported_grant_type'})

    return None

def get_access_token(token_view, request, user, scope=constants.SCOPES[0][0]):
    client = token_view.authenticate(request)
    access_token = token_view.get_access_token(request, user, scope, client)
    return access_token


def get_thumbnail_size(screen, position):  # position:list, detail
    Screen = namedtuple('Screen', ['width', 'height'])
    if position == 'detail':
        return Screen(1080, 600)

    if position == 'list':
        if 0 < screen.width <= 1000:
            return Screen(360, 200)
        elif 1000 < screen.width:
            return Screen(540, 300)

    return Screen(540, 300)


def get_screen_size(request):
    height_str = _get_request_header(request, 'HTTP_HEIGHT')
    width_str = _get_request_header(request, 'HTTP_WIDTH')
    height = int(height_str) if height_str else 0
    width = int(width_str) if width_str else 0
    Screen = namedtuple('Screen', ['width', 'height'])

    return Screen(width, height)


class CacheResponse(object):
    def __init__(self, timeout=60*3, key_func=None):
        self.timeout = timeout
        self.key_func = self.default_calculate_key if not key_func else key_func
        self.cache = cache

    def default_calculate_key(self, view_instance, view_method, request, args, kwargs):
        domain = str(request.META.get('HTTP_HOST')) + '.'
        cache_key = domain + "cache_api_response." + request.path
        return cache_key

    def __call__(self, func):
        this = self
        @wraps(func)
        def inner(self, request, *args, **kwargs):
            return this.process_cache_response(
                view_instance=self,
                view_method=func,
                request=request,
                args=args,
                kwargs=kwargs,
            )
        return inner

    def process_cache_response(self, view_instance, view_method, request, args, kwargs):
        key = self.calculate_key(
            view_instance=view_instance,
            view_method=view_method,
            request=request,
            args=args,
            kwargs=kwargs
        )
        response = self.cache.get(key)
        if not response:
            response = view_method(view_instance, request, *args, **kwargs)
            response = view_instance.finalize_response(request, response, *args, **kwargs)
            response.render()  # should be rendered, before picklining while storing to cache
            self.cache.set(key, response, self.timeout)
        if not hasattr(response, '_closable_objects'):
            response._closable_objects = []
        return response

    def calculate_key(self, view_instance, view_method, request, args, kwargs):
        key_func = self.key_func
        return key_func(
            view_instance=view_instance,
            view_method=view_method,
            request=request,
            args=args,
            kwargs=kwargs,
        )

cache_response = CacheResponse
