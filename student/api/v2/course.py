# -*- coding: utf-8 -*-
import logging
import time
import json
import random

from django.utils import timezone, dateparse
from django.core import cache
from django.db import transaction
from django.db.models import Q
from django.conf import settings

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.modulestore import (get_course_updates, get_item, get_items, get_course)
from api.v2.serializer import (
    CourseSerializer, CourseWithCategorySerializer, CourseDetailSerializer,
    StaffSerializer, CategorySerializer, KnowledgeMapSerializer, QASerializer,
    UpdateSerializer, ChapterSerializer, SequentialSerializer,
    VerticalsWithChildrenSerializer, VideoSerializer, ChapterWithSequentialSerializer,
    FragmentKnowledgeSerializer)
from api.utils import exclude_vpc_and_selfpaced_enrollments, get_screen_size, get_thumbnail_size
from api.v2.views import APIView
from course_meta.models import Course, HomepageCourses, Follow, HomepageFragmentKnowledge
from course_modes.models import CourseMode
from courseware.access import has_access
from courseware.views import get_current_child, save_child_position
from courseware.model_data import FieldDataCache
from courseware.module_render import toc_for_course, get_module_for_descriptor
from datetime import datetime, timedelta
from dogapi import dog_stats_api
from pytz import UTC, timezone as pytz_timezone
from student.models import CourseEnrollment
from student.views import course_from_key
from track.views import server_track
from xmodule.modulestore.exceptions import ItemNotFoundError
from collections import defaultdict
from credential.models import Coupon, get_credential_list_by_user
from xblock.runtime import KeyValueStore
from xblock.fields import Scope
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator
import api.v2.error as error
from course_stat import stat as course_stat

# If we can't find a 'general' CACHE defined in settings.py, we simply fall back
# to returning the default cache. This will happen with dev machines.
try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache.cache

log = logging.getLogger(__name__)

class CoursesView(APIView):

    def get(self, request, format=None):
        """ Get all the courses. """
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
            'timestamp': int(request.GET.get('timestamp', 0)),
            'with_category': request.GET.get('with_category', 1),
            'categories': request.GET.get('categories', '')
        }

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='list')

        categories = [each for each in param['categories'].split(',') if each]
        verified_courses_id = CourseMode.get_verified_option_courses()
        query = Course.exclude_vpc().filter(status__gte=0, course_type=0).exclude(course_id__in=verified_courses_id)
        if param['timestamp']:
            query = query.filter(
                modified__gt=datetime.utcfromtimestamp(param['timestamp']))
        if categories:
            query = query.filter(category__id__in=categories).distinct()

        total = query.count()
        courses = query[param['offset']:param['offset'] + param['limit']]
        result = {
            "courses": CourseWithCategorySerializer(thumbnail_size, courses, many=True).data if param['with_category'] else CourseSerializer(thumbnail_size, courses, many=True).data,
            "total": total,
        }
        return Response(result)


class HotCoursesView(APIView):

    def get(self, request, format=None):
        """ Get all the hot courses. """

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='list')
        homepage_courses = HomepageCourses.objects.select_related('course').filter(course__course_type=0).order_by('order')[0:8]
        courses = [hc.course for hc in homepage_courses]
        result = {
            "courses": CourseSerializer(thumbnail_size, courses, many=True).data
        }
        return Response(result)


class HotFragmentKnowledgeView(APIView):

    def get(self, request, format=None):
        """ Get all the hot courses. """

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='list')
        homepage_fragments = HomepageFragmentKnowledge.objects.filter(enabled=True, is_draft=False).order_by('order')[0:8]
        fragments = [hf.fragment for hf in homepage_fragments]
        params = {
            'thumbnail_size': thumbnail_size,
        }
        result = {
            "fragments": FragmentKnowledgeSerializer(fragments, many=True, context=params).data
        }
        return Response(result)


class RecentCoursesView(APIView):

    def get(self, request, format=None):
        """ Get all the recent courses. """
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
        }

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='detail')
        local_tz = pytz_timezone(settings.TIME_ZONE)
        now = datetime.now(local_tz)
        recent_time = datetime(now.year, now.month, now.day, tzinfo=local_tz)
        recent_utc_time = recent_time.astimezone(UTC)
        verified_courses_id = CourseMode.get_verified_option_courses()
        query = Course.exclude_vpc().filter(
            status__gte=0, start__gt=recent_utc_time, course_type=0).exclude(course_id__in=verified_courses_id).order_by('start')
        total = query.count()
        courses = query[param['offset']:param['offset'] + param['limit']]
        result = {
            "courses": CourseSerializer(thumbnail_size, courses, many=True).data,
            "total": total,
        }
        return Response(result)


class EnrollCoursesView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        """ Get the courses that user has enrolled, sort by enroll time. """
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
        }

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='detail')
        enrollments = exclude_vpc_and_selfpaced_enrollments(request.user)
        total = len(enrollments)
        courses = []
        for e in enrollments[param['offset']:param['offset'] + param['limit']]:
            try:
                courses.append(Course.objects.get(course_id=e.course_id))
            except:
                pass
        result = {
            "courses": CourseSerializer(thumbnail_size, courses, many=True).data,
            "total": total,
        }
        return Response(result)


class CoursesUpdateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        """ Get all the updates(notifications) of the enrolled courses. """
        param = {
            'timestamp': int(request.GET.get('timestamp', 0)),
        }

        enrollments = exclude_vpc_and_selfpaced_enrollments(request.user)
        courses = [Course.objects.get(course_id=e.course_id)
                   for e in enrollments]

        result = {
            "updates": [],
        }

        for course in courses:
            updates = get_course_updates(course.course_id, param['timestamp'])
            result["updates"] += UpdateSerializer(updates, many=True).data

        return Response(result)


class CourseDetailView(APIView):

    def get(self, request, course_id, format=None):
        """ Get course details. """
        params = {
            'without_chapters': int(request.GET.get('without_chapters', 0)),
            'without_qas': int(request.GET.get('without_qas', 0)),
            'display_recommend_courses': int(request.GET.get('display_recommend_courses', 0)),
        }

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='detail')

        try:
            course = Course.objects.get(course_id=course_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        result = CourseDetailSerializer(thumbnail_size, course, context=params).data

        if params['display_recommend_courses'] > 0:
            qset = Course.objects.filter((~Q(status=-1)) & (Q(course_type=1))).exclude(id=course.id)
            count = qset.count()
            if count > params['display_recommend_courses']:
                slice = random.random() * (count - params['display_recommend_courses'])
                r_cs = qset[slice: slice + params['display_recommend_courses']]
            else:
                r_cs = qset

            r_params = {
                'without_chapters': 1,
                'without_qas': 1,
                'display_recommend_courses': 0,
            }
            result['recommend_courses'] = []
            for course in r_cs:
                result['recommend_courses'].append(CourseDetailSerializer(thumbnail_size, course, context=r_params).data)
        else:
            result['recommend_courses'] = []

        return Response(result)


class CourseCategoryView(APIView):

    def get(self, request, course_id, format=None):
        """ Get course's categories. """
        try:
            course = Course.objects.get(course_id=course_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        result = {
            "categories": CategorySerializer(course.category.all(), many=True).data
        }
        return Response(result)


class CourseKnowledgeMapView(APIView):

    def get(self, request, course_id, format=None):
        """ Get course's categories. """
        try:
            course = Course.objects.get(course_id=course_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        knowledgemaps = [
            ckm.map_id for ckm in course.courseinknowledgemap_set.all()]
        result = {
            "knowledgemaps": KnowledgeMapSerializer(knowledgemaps, many=True).data
        }
        return Response(result)


class CourseStaffView(APIView):

    def get(self, request, course_id, format=None):
        """ Get course details. """
        try:
            course = Course.objects.get(course_id=course_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        result = {
            "staffs": []
        }
        for cs in course.coursestaffrelationship_set.all():
            staff = StaffSerializer(cs.staff).data
            staff['role'] = cs.role
            result["staffs"].append(staff)
        return Response(result)


class CourseQAView(APIView):

    def get(self, request, course_id, format=None):
        """ Get course QAs. """
        try:
            course = Course.objects.get(course_id=course_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        result = {
            "qas": QASerializer(course.courseqa_set.all(), many=True).data
        }
        return Response(result)


class EnrollCourseView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id, format=None):
        """ Get Get if user has permission to enroll the current course. """
        user = request.user
        is_enrolled = CourseEnrollment.is_enrolled(user, course_id)
        if not is_enrolled:
            raise error.Error(error.USER_NOT_ENROLLED, u'未加入课程')

        return Response(status=status.HTTP_204_NO_CONTENT)


    def post(self, request, course_id, format=None):
        """ Get Enroll the current course. The new version edX has lot of enroll modes. """
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    
        user = request.user
        try:
            course = course_from_key(course_key)
        except ItemNotFoundError:
            return error.ErrorResponse(error.INVALID_PARAMETER, "Course id is invalid", status=status.HTTP_404_NOT_FOUND)

        if not has_access(user, 'enroll', course):
            return error.ErrorResponse(error.INVALID_ENROLLMENT, "Enrollment is closed", status=status.HTTP_400_BAD_REQUEST)

        if CourseEnrollment.is_course_full(course):
            return error.ErrorResponse(error.INVALID_ENROLLMENT, "Course is full", status=status.HTTP_400_BAD_REQUEST)

        available_modes = CourseMode.modes_for_course(course_id)
        available_modes_dict = CourseMode.modes_for_course_dict(course_id, available_modes)
        if CourseMode.has_verified_mode(available_modes_dict):
            return error.ErrorResponse(error.INVALID_ENROLLMENT, "付费课程请在网站加入", status=status.HTTP_400_BAD_REQUEST)
        current_mode = available_modes[0]

        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        dog_stats_api.increment(
            "common.student.enrollment",
            tags=["org:{0}".format(course_key.org),
                  "course:{0}".format(course_key.course),
                  "run:{0}".format(course_key.run)]
        )
        server_track(request, 'api.course.enrollment', {
            'username': user.username,
            'course_id': course_id,
        })

        CourseEnrollment.enroll(user, course.id, mode=current_mode.slug)
        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request, course_id, format=None):
        """ Unenroll the current course. """
        user = request.user
        if not CourseEnrollment.is_enrolled(user, course_id):
            return error.ErrorResponse(error.USER_NOT_ENROLLED, "Course id is invalid", status=status.HTTP_404_NOT_FOUND)
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        CourseEnrollment.unenroll(user, course_key)
        dog_stats_api.increment(
            "common.student.unenrollment",
            tags=["org:{0}".format(course_key.org),
                  "course:{0}".format(course_key.course),
                  "run:{0}".format(course_key.run)]
        )
        server_track(request, 'api.course.unenrollment', {
            'username': user.username,
            'course_id': course_id,
        })
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseUpdateView(APIView):

    def get(self, request, course_id, format=None):
        """ Get updates of the current course. """
        if not Course.objects.filter(course_id=course_id)[0]:
            return Response(status=status.HTTP_404_NOT_FOUND)

        param = {
            'timestamp': int(request.GET.get('timestamp', 0)),
        }

        updates = get_course_updates(course_id, param['timestamp'])
        result = {
            "updates": UpdateSerializer(updates, many=True).data
        }
        return Response(result)


class CourseEnrollmentsView(APIView):

    def get(self, request, course_id, format=None):
        """ Get enrollment number of the current course. """
        result = {
            "enrollments": course_stat.enrollment_total_count(
                SlashSeparatedCourseKey.from_deprecated_string(course_id)),
        }
        return Response(result)


class CourseCommentsView(APIView):

    def get(self, request, course_id, format=None):
        """ Get comment number of the current course. """
        result = {
            "comments": course_stat.comment_total_count(
                SlashSeparatedCourseKey.from_deprecated_string(course_id)),
        }
        return Response(result)


class CourseFreqDataView(APIView):

    def get(self, request, course_id, format=None):
        """ Get some frequency update data of the current course. """
        try:
            course = Course.objects.get(course_id=course_id)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)

        result = {
            "enrollments": course_stat.enrollment_total_count(course_key),
            "comments": course_stat.comment_total_count(course_key),
            "serialized": course.serialized,
        }
        return Response(result)

class CourseChaptersView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id, format=None):
        """ Get course chapter list.
        注意:如果移动端需要的vertical_types需要video之外的东西，整个方法需要重构
        """
        if not Course.objects.filter(course_id=course_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not CourseEnrollment.is_enrolled(request.user, course_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'androidtv' in user_agent:
            is_tv = True
        else:
            is_tv = False

        show_sequentials = request.GET.get('show_sequentials')
        if show_sequentials:
            if show_sequentials == '1' or show_sequentials.lower() == 'true':
                show_sequentials = True
            else:
                show_sequentials = False
        # 首先取一下缓存
        if show_sequentials:
            # 手动清除缓存的后面
            invalite_cache = request.GET.get('cache', None)
            if invalite_cache:
                cache_key_tv = 'api.course.{}.chapters_with_seq.{}'.format(course_id, True)
                cache_key = 'api.course.{}.chapters_with_seq.{}'.format(course_id, False)
                cache.delete(cache_key_tv)
                cache.delete(cache_key)

            if settings.DEBUG:
                cache_key = 'api.course.{}.chapters_with_seq.{}'.format(course_id, is_tv) + str(time.time())
            else:
                cache_key = 'api.course.{}.chapters_with_seq.{}'.format(course_id, is_tv)

            cache_result = cache.get(cache_key)
            if cache_result:
                return Response(cache_result)

        course = get_course(course_id)
        chapters = [get_item(course_id, "chapter", chapter_id)
                    for chapter_id in _get_item_id_list(course.children, "chapter")]
        now = datetime.now(UTC)
        chapters = filter(lambda x: x and x.start < now, chapters)

        if show_sequentials:
            # key sequential, value {video:0}
            seq_type_dict = defaultdict(lambda : defaultdict(int))

            # 首先查出vertical需要的block列表
            vertical_types = ['video']
            vertical_dict = {vt: set() for vt in vertical_types}
            for vtype in vertical_types:
                blocks = get_items(course_id, vtype)
                blocks = filter(lambda x: x and x.start < now, blocks)
                vtype_set = _get_vertical_set(blocks)
                vertical_dict[vtype] = vtype_set

            for chapter in chapters:
                sequentials = [get_item(course_id, "sequential", sequential_id)
                               for sequential_id in _get_item_id_list(chapter.children, "sequential")]
                sequentials = filter(lambda x: x and x.start < now, sequentials)
                chapter.sequentials = sequentials

                for sequential in sequentials:
                    verticals = [get_item(course_id, "vertical", vertical_id)
                                 for vertical_id in _get_item_id_list(sequential.children, "vertical")]
                    verticals = filter(lambda x: x and x.start < now, verticals)
                    sequential.verticals = verticals

                    # 通过之前查出的block集合
                    for vertical in verticals:
                        blocks = vertical.children
                        for block in blocks:
                            category = _get_location_category(block)
                            block_location_id = _get_location_id(block)
                            if category in vertical_dict and block_location_id in vertical_dict[category]:
                                seq_type_dict[sequential][category] += 1

            for sequential, types in seq_type_dict.iteritems():
                sequential.type = dict(types)

            chapters_array = ChapterWithSequentialSerializer(chapters, many=True).data

            if is_tv:
                cp_array = []
                for chapters_temp in chapters_array:
                    sq_array = []
                    for sq_temp in chapters_temp['sequentials']:
                        if sq_temp['type'].get('video', None):  # tv端过滤非video
                            sq_array.append(sq_temp)
                    chapters_temp['sequentials'] = sq_array
                    if chapters_temp['sequentials'] !=[]:
                        cp_array.append(chapters_temp)
                chapters_array = cp_array

            result = {
                "chapters": chapters_array,
            }
            if is_tv:
                cache.set(cache_key, result, 60 * 60 * 24 * 7)
            else:
                cache.set(cache_key, result, 60 * 60)
        else:
            result = {
                "chapters": ChapterSerializer(chapters, many=True).data
            }
        return Response(result)


class CourseChapterView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id, chapter_id, format=None):
        """ Get sequential list of the current chapter. """
        if not Course.objects.filter(course_id=course_id)[0]:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not CourseEnrollment.is_enrolled(request.user, course_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        chapter = get_item(course_id, "chapter", chapter_id)
        sequentials = [get_item(course_id, "sequential", sequential_id)
                       for sequential_id in _get_item_id_list(chapter.children, "sequential")]
        now = datetime.now(UTC)
        sequentials = filter(lambda x: x and x.start < now, sequentials)

        result = {
            "sequentials": SequentialSerializer(sequentials, many=True).data
        }
        return Response(result)


class CourseSequentialView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id, sequential_id, format=None):
        """ Get vertical list of the current chapter. """
        if not Course.objects.filter(course_id=course_id):
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not CourseEnrollment.is_enrolled(request.user, course_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        param = {
            'category': request.GET.get('category', 'video'),
        }
        sequential = get_item(course_id, "sequential", sequential_id)
        verticals = [get_item(course_id, "vertical", vertical_id)
                     for vertical_id in _get_item_id_list(sequential.children, "vertical")]
        now = datetime.now(UTC)
        verticals = filter(lambda x: x and x.start < now, verticals)

        for vertical in verticals:
            children = [get_item(course_id, param['category'], item_id)
                        for item_id in _get_item_id_list(vertical.children, param['category'])]
            children = filter(lambda x: x and x.start < now, children)
            vertical.children = children

        result = {
            "verticals": VerticalsWithChildrenSerializer(course_id, verticals, many=True).data
        }

        return Response(result)


class CourseVerticalView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id, vertical_id, format=None):
        """ Get vertical list of the current chapter. """
        if not Course.objects.filter(course_id=course_id)[0]:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not CourseEnrollment.is_enrolled(request.user, course_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        param = {
            'category': request.GET.get('category', 'video'),
        }

        vertical = get_item(course_id, "vertical", vertical_id)
        children = [get_item(course_id, "video", item_id)
                    for item_id in _get_item_id_list(vertical.children, param['category'])]
        now = datetime.now(UTC)
        children = filter(lambda x: x and x.start < now, children)

        result = {
            # TODO: Select the other serializers
            "children": VideoSerializer(course_id, children, many=True).data
        }
        return Response(result)


class FollowCourseView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id):
        user = request.user
        is_followed = Follow.objects.filter(
            user=user,
            target_type='course_meta.models.Course',
            target_id=course_id
        ).exists()
        status = u"已关注" if is_followed else u"未关注"

        result = {'status': status}
        return Response(result)

    def post(self, request, course_id):
        user = request.user
        Follow.follow(user, 'course_meta.models.Course', course_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, course_id):
        user = request.user
        Follow.unfollow(user, 'course_meta.models.Course', course_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowCoursesView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
        }

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='list')
        user = request.user
        _followed_course = Follow.targets(user, 'course_meta.models.Course')
        followed_course = _followed_course.filter(course_type=0)
        total = followed_course.count()
        courses = followed_course[param['offset']:param['offset'] + param['limit']]
        result = {
            "courses": CourseSerializer(thumbnail_size, courses, many=True).data,
            "total": total,
        }
        return Response(result)

    @transaction.commit_manually
    def delete(self, request):
        courses = request.DATA.get('courses', '')
        course_ids = courses.split(',')
        user = request.user
        try:
            for course_id in course_ids:
                if course_id:
                    Follow.unfollow(user, 'course_meta.models.Course', course_id)
        except:
            transaction.rollback()
            raise error.Error(error.COURSES_FOLLOW_FAILED, u"课程取消关注失败")
        else:
            transaction.commit()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HonorView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
        }
        user = request.user
        credential_list = get_credential_list_by_user(request.user)
        should_del = ['credential', 'credential_jpg']
        credentail_seri_list = []
        total = len(credential_list)
        credential_list = credential_list[param['offset']:param['offset'] + param['limit']]
        for credential in credential_list:
            for sd in should_del:
                if sd in credential:
                    del credential[sd]
            _credential = get_credential_dict(credential, user)
            credentail_seri_list.append(_credential)
        result = {
            "honors": credentail_seri_list,
            "total": total,
        }
        return Response(result)

class UserCourseStatus(APIView):
    """
    **Use Case**
        Get or update the ID of the module that the specified user last visited in the specified course.
    **Example request**:
        GET /api/mobile/v0.5/users/{username}/course_status_info/{course_id}
        PATCH /api/mobile/v0.5/users/{username}/course_status_info/{course_id}
            body:
                last_visited_module_id={module_id}
                modification_date={date}
            The modification_date is optional. If it is present, the update will only take effect
            if the modification_date is later than the modification_date saved on the server.
    **Response Values**
        * last_visited_module_id: The ID of the last module visited by the user in the course.
        * last_visited_module_path: The ID of the modules in the path from the
          last visited module to the course module.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id):
        """
        Get the ID of the module that the specified user last visited in the specified course.
        """
        try:
            course = get_course(course_id)
            if not course:
                return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception as ex:
            log.error(ex)
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(self._get_course_info(request, course))


    def post(self, request, course_id):
        """
        Update the ID of the module that the specified user last visited in the specified course.
        """
        chapter_id = request.DATA.get("chapter_id")
        sequential_id = request.DATA.get("sequential_id")
        modification_date_string = request.DATA.get("timestamp")
        if not chapter_id:
            return self.get(request, course_id)
        if not modification_date_string or len(modification_date_string) != 13:
            raise error.Error(error.INVALID_PARAMETER, '参数错误: timestamp')
        return Response(self._modify_course_status(request, course_id,
            chapter_id, sequential_id, modification_date_string))

    def _last_visited_module_path(self, request, course):
        """
        Returns the path from the last module visited by the current user in the given course up to
        the course module. If there is no such visit, the first item deep enough down the course
        tree is used.
        """
        field_data_cache = FieldDataCache.cache_for_descriptor_descendents(
            course.id, request.user, course, depth=2)

        course_module = get_module_for_descriptor(request.user, request, course, field_data_cache, course.id)

        path = [course_module]
        chapter = get_current_child(course_module)
        if chapter is not None:
            path.append(chapter)
            section = get_current_child(chapter)
            if section is not None:
                path.append(section)

        path.reverse()
        return path

    def _get_course_info(self, request, course, chapter=None, sequential=None):
        """
        Returns the course status

        edx:

        path_ids = [unicode(module.location) for module in path]
        return Response({
           "last_visited_module_id": path_ids[0],
           "last_visited_module_path": path_ids,
        })

        {
            "last_visited_module_id": "i4x://apitestorg/apitestcourse/sequential/624e6b343d5e4b319a6a8b7fe63c9262",
            "last_visited_module_path": [
                "i4x://apitestorg/apitestcourse/sequential/624e6b343d5e4b319a6a8b7fe63c9262",
                "i4x://apitestorg/apitestcourse/chapter/a9ae78343c0f47ad91159d3b9035ea9c",
                "i4x://apitestorg/apitestcourse/course/2015_3"
            ]
        }
        """
        path = self._last_visited_module_path(request, course)
        path_ids = [(module.location) for module in path]
        course_id = course.id
        chapter_id = ''
        sequential_id = ''
        chapter_location = ''
        sequential_location = ''
        result = {'course_id': _get_course_id(course_id)}
        for path_id in path_ids:
            if u'chapter' == path_id.block_type:
                chapter_id = path_id.block_id
                chapter_location = _get_location_id(path_id)
                continue
            if u'sequential' == path_id.block_type:
                sequential_id = path_id.block_id
                sequential_location =_get_location_id(path_id)
                continue
        # chapter
        if not chapter_id:
            return result

        cache_course_children_key = 'api_course_sync.course.{}.chapter'.format(course.id)
        # 如果缓存有course_children，则说明下面的mongo查chapter查到了
        course_children = cache.get(cache_course_children_key, [])
        if not course_children:
            try:
                chapter = get_item(course.id, 'chapter', chapter_id) if not chapter else chapter
                if not chapter:
                    return result
            except ItemNotFoundError:
                return result
            course_children = get_obj_children_ids(course)
            cache.set(cache_course_children_key, course_children, 60 * 60)
        chapter_position = 0 if chapter_location not in course_children else course_children.index(chapter_location)
        result['chapter_id'] = chapter_id
        result['chapter_position'] = chapter_position
        # sequential
        if sequential_id:
            try:
                cache_chapter_children_key = 'api_course_sync.course.{}.chapter.{}.sequential'.format(course.id,
                                                                                                      chapter_id)
                visit_chapter_sequentials = cache.get(cache_chapter_children_key, [])
                if not visit_chapter_sequentials:
                    chapter = get_item(course.id, 'chapter', chapter_id) if not chapter else chapter
                    sequential = get_item(course.id, 'sequential', sequential_id) if not sequential else sequential
                    if sequential:
                        visit_chapter_sequentials = get_obj_children_ids(chapter)
                        cache.set(cache_chapter_children_key, visit_chapter_sequentials, 60 * 60)

                sequential_position = 0 if sequential_location not in visit_chapter_sequentials \
                    else visit_chapter_sequentials.index(sequential_location)
                result['sequential_id'] = sequential_id
                result['sequential_position'] = sequential_position
            except ItemNotFoundError:
                raise error.Error(status=status.HTTP_404_NOT_FOUND)
        return result

    def save_sequential_position(self, course, chapter, sequential):
        if course and hasattr(course, 'position'):
            save_child_position(course, chapter.location.name)
        if chapter and hasattr(chapter, 'position'):
            save_child_position(chapter, sequential.location.name)

    def _update_last_visited_sequential(self, request, course, chapter_id, sequential_id, modification_date):
        '''
        course -- xmodule
        '''
        field_data_cache = FieldDataCache.cache_for_descriptor_descendents(
            course.id, request.user, course, depth=2)
        try:
            chapter_descriptor = get_item(course.id, 'chapter', chapter_id)
            sequential_descriptor = get_item(course.id, 'sequential', sequential_id)
        except ItemNotFoundError:
            raise error.Error(status=status.HTTP_404_NOT_FOUND)
        course_descriptor = course
        course = get_module_for_descriptor(
                request.user, request, course_descriptor, field_data_cache, course.id)
        chapter = get_module_for_descriptor(
                request.user, request, chapter_descriptor, field_data_cache, course.id)
        sequential = get_module_for_descriptor(
                request.user, request, sequential_descriptor, field_data_cache, course.id)
        if modification_date:
            key = KeyValueStore.Key(
                scope=Scope.user_state,
                user_id=request.user.id,
                block_scope_id=course.location,
                field_name=None
            )
            student_module = field_data_cache.find(key)
            if student_module:
                original_store_date = student_module.modified
                if modification_date < original_store_date:
                    # old modification date so skip update
                    return self._get_course_info(request, course)

        self.save_sequential_position(course, chapter, sequential)
        return self._get_course_info(request, course)

    def _modify_course_status(self, request, course_id, chapter_id, sequential_id, modification_date_string):
        modification_date = None
        try:
            course = get_course(course_id)
        except Exception:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not course:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if modification_date_string:
            modification_date = dateparse.parse_datetime(modification_date_string)
            if not modification_date or not modification_date.tzinfo:
                try:
                    modification_date = datetime.utcfromtimestamp(int(modification_date_string) / 1000.0)
                    # 应该通过0时区对比
                    modification_date = timezone.make_aware(modification_date, timezone.utc)
                except Exception:
                    modification_date = None

        if sequential_id:
            return self._update_last_visited_sequential(request, course, chapter_id, sequential_id, modification_date)
        else:
            # The arguments are optional, so if there's no argument just succeed
            return self._get_course_info(request, course)


class UserCoursesStatus(UserCourseStatus):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        courses = request.GET.get("courses", "[]")
        courses = json.loads(courses)
        result = []
        for course in courses:
            course_id = course.get('course_id')
            if not course_id:
                continue
            try:
                course = get_course(course_id)
            except Course.DoesNotExist:
                continue
            result.append(self._get_course_info(request, course))
        return Response({'courses': result})


    def post(self, request):
        """
        Update the ID of the module that the specified user last visited in the specified course.
        """
        courses = request.DATA.get("courses", "[]")
        courses = json.loads(courses)
        result = []
        for course in courses:
            course_id = course.get('course_id')
            chapter_id = course.get('chapter_id')
            sequential_id = course.get('sequential_id')
            modification_date_string = course.get("timestamp")
            if not course_id:
                continue
            if not chapter_id:
                try:
                    course = get_course(course_id)
                    if course:
                        result.append(self._get_course_info(request, course))
                except Exception as ex:
                    log.info(ex)
                    continue
            else:
                result.append(self._modify_course_status(request, course_id, chapter_id, sequential_id, modification_date_string))
        return Response({'courses': result})


def get_credential_dict(credential, user):
    HONOR_THUMBNAIL_TEMPLATE = 'http://storage.xuetangx.com/public_assets/xuetangx/api/certificate/{}.png'
    HONOR_THUMBNAIL_1080_TEMPLATE = 'http://storage.xuetangx.com/public_assets/xuetangx/credential/thumbnail/{}_1080.jpg'
    # HONOR_THUMBNAIL_720_TEMPLATE = 'http://storage.xuetangx.com/public_assets/xuetangx/credential/thumbnail/{}_720.jpg'
    _credential = {
        'course_id': '',
        'display_name': '',
        'study_start': '',
        'study_end': '',
        'honor_date': '',
        'honor_org': '',
        'honor_type': '',
        'download_url': '',
        'src_url': '',
        'thumbnail': '',
        # TODO: 移动端以后可能会要
        'alt': '',
    }
    course_id = credential.get('course_id','')
    thumbnail_id = sum(map(ord, course_id)) % 6 + 1
    credential_id = credential.get('credential_id', '')
    honor_orgs = [u'学堂在线']
    authorization_zh_cn = credential.get('authorization_zh_cn')
    if authorization_zh_cn:
        honor_orgs.append(authorization_zh_cn)
    try:
        course = Course.objects.get(course_id=course_id)
        _credential['study_start'] = course.start if course.start else ''
        _credential['study_end'] = course.end if course.end else ''
    except Course.DoesNotExist:
        logging.error('user({}) has a credential({}) but he dont hava course({}) record'.format(
        user.id, credential_id, course_id
    ))

    _credential['course_id'] = course_id
    _credential['display_name'] = credential.get('text_info', {}).get('course_name_zh_cn', '')
    _credential['honor_date'] = credential.get('date_info', {}).get('issue_date', '')
    _credential['honor_type'] = u'认证证书' if credential.get('user_info', {}).get('verified') else u'普通证书'
    _credential['honor_org'] = honor_orgs
    _credential['download_url'] = 'http://{}/download_credential/{}.pdf'.format(
        settings.SITE_NAME, credential_id) if credential_id else ''
    _credential['src_url'] = HONOR_THUMBNAIL_1080_TEMPLATE.format(credential_id)
    _credential['thumbnail'] = HONOR_THUMBNAIL_TEMPLATE.format(thumbnail_id)
    return _credential


def _get_item_id_list(data, category=""):
    result = []
    offset = len(category) + 1
    for s in data:
        if isinstance(s, BlockUsageLocator):
            result.append(s.block_id)
        else:
            if str(s).find('/') > 0:
                sub_str = category + '/'
            else:
                sub_str = category + '+'

            rindex = str(s).rfind(sub_str)
            if rindex >= 0:
                result.append(str(s)[rindex + offset:])
    return result


def _get_location_category(location):
    try:
        if isinstance(location, BlockUsageLocator):
            category = location.block_type
        else:
            category = location.split('/')[-2]
    except Exception, e:
        log.error(e)
        category = ''
    return category

def _get_location_id(location):
    try:
        if isinstance(location, BlockUsageLocator):
            category = (location.block_id)
        else:
            category = location.split('/')[-1]
    except Exception, e:
        log.error(e)
        category = ''
    return category

def _get_vertical_set(blocks):
    vtype_set = []
    for block in blocks:
        if isinstance(block.location, BlockUsageLocator):
            b_id = str(block.location.block_id)
            vtype_set.append(b_id)
        else:
            b_id = block.location.url()
            vtype_set.append(b_id)
    return vtype_set



def get_obj_children_ids(obj):
    s_set = []
    for block_l in obj.children:
        if isinstance(block_l, BlockUsageLocator):
            b_id = str(block_l.block_id)
            s_set.append(b_id)
        else:
            b_id = block_l.url()
            s_set.append(b_id)
    return s_set

def _get_course_id(course_):
    try:
        if isinstance(course_, CourseLocator):
            course_id_str = str(course_)
            log.info(course_id_str)
        else:
            course_id_str = course_
    except Exception, e:
        log.error(e)
        course_id_str = ''
    return course_id_str
