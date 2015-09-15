# -*- coding: utf-8 -*-
import re
import requests
from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.core import cache
from django.utils.timezone import UTC
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from student.models import CourseEnrollment
from course_modes.models import CourseMode
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from .modules import *
from course_meta.models import (CourseCategory,
                                Staff, Course, CourseInKnowledgeMap, CourseQA, HomepageCourses)
from course_meta.utils import naturalFormatDate
from api.utils import new_search
from api.modulestore import get_course_updates, get_item, get_course
from api.utils import exclude_vpc_and_selfpaced_enrollments

from api.v2.course import _get_item_id_list
from api.v2.serializer import _normalizeUrl
from course_stat import stat as course_stat


class CoursenameList(APIView):

    def get(self, request, format=None):
        response = {
            'courses': [],
            'status': 'success'
        }

        courses = Course.exclude_vpc()
        for course in courses:
            course_dict = {}
            course_dict['id'] = course.course_id
            course_dict['display_name'] = course.name
            response['courses'].append(course_dict)

        return Response(response)


class CourseDetail(APIView):

    def get(self, request, format=None):
        try:
            course_id = request.REQUEST.get('course_id')
            course = Course.objects.get(course_id=course_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        response = fill_detail_in_course(course, request.user)
        return Response(response)


class AllCourses(APIView):

    def get(self, request, format=None):
        response = {}
        verified_courses_id = CourseMode.get_verified_option_courses()
        courses = Course.exclude_vpc().filter(
            status__gte=0, course_type=0).exclude(course_id__in=verified_courses_id).order_by('-status', '-id')
        response['data'] = fill_in_courses(courses, request.user)
        response['status'] = 'success'

        # Add selected for homepage courses and add knowledge_id for knowledge
        # map courses
        homepage_course_list = HomepageCourses.objects.order_by(
            "order")[0:8]
        selected_list = []
        for homepage_course in homepage_course_list:
            course = homepage_course.course
            selected_list.append(course.course_id)

        for course in response['data']:
            if course['course_id'] in selected_list:
                course['selected'] = True
            else:
                course['selected'] = False

        knowledge_list = {}
        knowledge_map_list = CourseInKnowledgeMap.objects.all()
        for c in knowledge_map_list:
            knowledge_list[c.course_id.course_id] = {
                'id': c.map_id_id,
                'level': c.level,
            }

        for course in response['data']:
            if course['course_id'] in knowledge_list:
                course['knowledge_map'] = knowledge_list[course['course_id']]
            else:
                course['knowledge_map'] = {}

        return Response(response)


class CourseByCategory(APIView):

    def get(self, request, category_id, format=None):
        response = {}
        try:
            category_obj = CourseCategory.objects.get(id=int(category_id))
        except Exception:
            response["status"] = "failed"
            return Response(response)
        else:
            courses = CourseCategory.objects.get(id=category_id).course_set.filter(
                status__gte=0, course_type=0).order_by('-status', '-id')
            response['category_id'] = category_id
            response['category'] = category_obj.name
            response['data'] = fill_in_courses(courses, request.user)
            response["status"] = "success"
        return Response(response)


class CourseSearch(APIView):

    def get(self, request, format=None):
        """ Search """
        # Get all the params and set default value
        parameters = {
            'query': request.REQUEST.get('query', ''),
            'started': int(request.REQUEST.get('started', 0)),
            'hasTA': int(request.REQUEST.get('hasTA', 0)),
        }
        if not parameters['started']:
            parameters['started'] = 'false'

        course_list, total_length = new_search(parameters['query'], started=parameters['started'],
                                               hasTA=parameters['hasTA'])

        response = fill_in_courses(course_list, request.user)
        return Response(response)


class CourseMessage(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_name, format=None):
        """ Get course navigational elements """
        course = get_course(course_name)
        now = datetime.now(UTC())

        # try:
        #     courses = CourseEnrollment.objects.get(
        #         user=request.user, course_id=course_name, is_active=True)
        # except:
        #     return Response(status=status.HTTP_404_NOT_FOUND)

        is_enrolled = CourseEnrollment.is_enrolled(request.user, course_name)
        if not is_enrolled:
            return Response(status=status.HTTP_404_NOT_FOUND)

        result = {
            "success": True,
            "course": {
                "display_name": course.display_name,
                "location": str(course.location),
                "start": course.start,
                "children": _get_children(course_name, course.children, 'chapter', now),
            }
        }

        chapters = result['course']['children']
        for chapter in chapters:
            sequentials = chapter['children'] = _get_children(
                course_name, chapter['children'], 'sequential', now)
            for sequential in sequentials:
                verticals = sequential['children'] = _get_children(
                    course_name, sequential['children'], 'vertical', now)
                for vertical in verticals:
                    children = [get_item(course_name, 'video', item_id) for item_id in _get_item_id_list(
                        vertical['children'], 'video')]
                    children = filter(lambda x: x and x.start < now, children)
                    vertical['children'] = []
                    course_key = SlashSeparatedCourseKey.from_string(course_name)
                    for video in children:
                        data = {
                            'display_name': video.display_name,
                            'location': str(video.location),
                            'start': video.start,
                            'track_zh': get_track_zh(video, course_key),
                            'track_en': get_track_en(video, course_key),
                            'source': get_video_source(video),
                        }
                        try:
                            ccsource = video.ccsource.strip()
                            data['length'] = VideoInfo.objects.get(
                                vid=ccsource).duration
                        except:
                            data['length'] = 0

                        vertical['children'].append(data)

        return Response(result)

def get_video_source(video):
    source_url = video.ccsource
    return source_url.strip()

def get_track_en(obj, course_key):
    value = obj.transcripts.get('en_xuetangx', '')
    if value:
        if course_key.deprecated:
            value = '/c4x/%s/%s/asset/%s' % (course_key.org, course_key.course, value)
        else:
            value = '/asset-v1:%s+%s+%s+type@asset+block@%s' % (course_key.org, course_key.course, course_key.run, value)
        return _normalizeUrl(value)
    else:
        return ''

def get_track_zh(obj, course_key):
    value = obj.transcripts.get('zh', '')
    if value:
        if course_key.deprecated:
            value = '/c4x/%s/%s/asset/%s' % (course_key.org, course_key.course, value)
        else:
            value = '/asset-v1:%s+%s+%s+type@asset+block@%s' % (course_key.org, course_key.course, course_key.run, value)
        return _normalizeUrl(value)
    else:
        return ''

def _get_children(course_id, children, category, now):
    result = []

    items = [get_item(course_id, category, item_id)
             for item_id in _get_item_id_list(children, category)]
    items = filter(lambda x: x and x.start < now, items)

    for item in items:
        data = {
            "display_name": item.display_name,
            "location": str(item.location),
            "start": item.start,
            "children": item.children,
        }
        result.append(data)

    return result

class CoursesUpdate(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        """ Get all course notification """
        user = request.user
        timestamp = request.REQUEST.get('timestamp', 0)

        courses = exclude_vpc_and_selfpaced_enrollments(user)
        updates_data = {'notifications': []}

        for c in courses:
            course_update = {}
            course_update['course_id'] = str(c.course_id)

            updates = get_course_updates(c.course_id, int(timestamp))
            for u in updates:
                u['id'] = "%s/N%06d" % (str(c.course_id), u['id'])
                u['date'] = u['date'].strftime("%B %d, %Y")
            course_update['updates'] = updates
            updates_data['notifications'].append(course_update)

        return Response(updates_data)


class CourseUpdate(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_name, format=None):
        """ Get course notificationes """
        timestamp = request.REQUEST.get('timestamp', 0)

        if not Course.objects.filter(course_id=course_name).count():
            return Response(status=status.HTTP_404_NOT_FOUND)

        updates = get_course_updates(course_name, int(timestamp))
        for u in updates:
            u['id'] = "%s/N%06d" % (course_name, u['id'])
            u['date'] = u['date'].strftime("%B %d, %Y")
        updates_data = {'notifications': updates}

        return Response(updates_data)


def fill_in_courses(courses, user):
    data = []
    for course in courses:
        data.append(fill_detail_in_course(course, user))

    return data


def fill_in_course(course, user=None):
    detail = {}
    detail['course_id'] = course.course_id
    detail['display_name'] = course.name
    detail['display_org'] = course.org
    detail['display_coursenum'] = course.course_num
    # detail['subtitle'] = course.subtitle
    # detail['video'] = course.intro_video
    # detail['thumbnail'] = course.thumbnail
    if course.start:
        detail['start'] = course.start.strftime("%Y-%m-%d %H:%M:%S")
        detail['naturalStart'] = naturalFormatDate(course.start)
    else:
        detail['start'] = ""
        detail['naturalStart'] = ""

    if course.end:
        detail['finish'] = course.end.strftime("%Y-%m-%d %H:%M:%S")
    else:
        detail['finish'] = ""

    if course.enrollment_start:
        detail['advertised_start'] = course.enrollment_start.strftime(
            "%Y-%m-%d %H:%M:%S")
    else:
        detail['advertised_start'] = ""

    if course.enrollment_end:
        detail['advertised_finish'] = course.enrollment_end.strftime(
            "%Y-%m-%d %H:%M:%S")
    else:
        detail['advertised_finish'] = ""

    if cmp(course.owner.lower(), 'edx') == 0:
        detail['course_status'] = '由edX联盟高校提供'
        # If this course is edx, give a later enrollment start time
        detail['advertised_start'] = '2030-01-01 00:00:00'
    elif course.serialized < 0:
        detail['course_status'] = '即将开课'
    elif course.serialized == 0:
        detail['course_status'] = '已上线'
    else:
        detail['course_status'] = '更新至第%d章' % course.serialized

    detail['student_num'] = course_stat.enrollment_total_count(
        SlashSeparatedCourseKey.from_deprecated_string(course.course_id))
    detail['course_image_url'] = _transform_thumbnail(course.thumbnail)
    detail['share_content'] = ""

    # lookup Course_staff table with course_id
    # problem: cannot get separate info of org, postion
    try:
        staff = Staff.objects.filter(course__course_id=course.course_id,
                                     coursestaffrelationship__role=0)[0]
        staff_dict = {}
        staff_dict['name'] = staff.name
        staff_dict['image_url'] = _normalizeImageUrl(staff.avartar)
        staff_dict['person_url'] = ""
    except:
        staff_dict = {}
        staff_dict['name'] = ""
        staff_dict['image_url'] = ""
        staff_dict['person_url'] = ""

    detail['master_teacher'] = staff_dict

    is_enrolled = user and not isinstance(user, AnonymousUser) and CourseEnrollment.is_enrolled(user, course.course_id)
    detail['enroll'] = is_enrolled

    return detail


def fill_detail_in_course(course, user):
    detail = fill_in_course(course, user)
    detail['status'] = 'success'
    detail['short_description'] = course.subtitle
    detail['effort'] = course.effort
    detail['outline'] = course.chapters
    detail['reserve'] = course.prerequisites
    detail['performance_evaluation'] = course.quiz
    detail['marketing_video_url'] = course.intro_video
    detail['marketing_caption_url'] = "http://s.xuetangx.com/files/course/caption/%s.srt" % course.intro_video if course.intro_video else ''

    # Assistant teachers
    detail['assistant'] = []
    staffs = Staff.objects.filter(course__course_id=course.course_id,
                                  coursestaffrelationship__role=1)
    for staff in staffs:
        staff_dict = {}
        staff_dict['name'] = staff.name
        staff_dict['image_url'] = _normalizeImageUrl(staff.avartar)
        staff_dict['person_url'] = ""
        detail['assistant'].append(staff_dict)

    detail['faq'] = []
    faqs = CourseQA.objects.filter(course_id=course).order_by('order')
    for f in faqs:
        faq = {}
        faq['question'] = f.question
        faq['answer'] = f.answer
        detail['faq'].append(faq)

    categories = course.category.all()
    detail['categories'] = []
    for category in categories:
        category_dict = {}
        category_dict['id'] = category.id
        detail['categories'].append(category_dict)

    return detail


def _normalizeImageUrl(url):
    if not url or re.match('^(https?:)?//', url):
        return url
    return "http://www.xuetangx.com/%s" % url.lstrip("/")


# If we can't find a 'general' CACHE defined in settings.py, we simply fall back
# to returning the default cache. This will happen with dev machines.
try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache.cache


def _transform_thumbnail(value):
    m = re.match('^https?://s.xuetangx.com/files/course/image/(.*)$', value)
    if m:
        return "http://s.xuetangx.com/files/course/image/large/%s" % m.group(1)

    if value.startswith('http'):
        return value

    cache_key = "api_thumbnail_cache." + value
    url = cache.get(cache_key)
    if url:
        return url
    # log.info("Thumbnail cache not hit: %s" % value)

    try:
        url = "http://s.xuetangx.com/%s" % value.lstrip('/')
        r = requests.head(url)
        if r.status_code == status.HTTP_200_OK:
            cache.set(cache_key, url, 60 * 60 * 24)
            return url
    except:
        pass

    url = "http://www.xuetangx.com/%s" % value.lstrip("/")
    cache.set(cache_key, url, 60 * 60 * 24)
    return url
