from .course import fill_in_courses

from course_meta.models import Course
from courseware.access import has_access
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from dogapi import dog_stats_api
from student.models import CourseEnrollment
from student.views import course_from_key
from track.views import server_track
from xmodule.modulestore.exceptions import ItemNotFoundError
from course_modes.models import CourseMode
from api.utils import exclude_vpc_and_selfpaced_enrollments
from opaque_keys.edx.locations import SlashSeparatedCourseKey

class EnrollmentList(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        """ Get list of enrolled courses for user """
        enrollments = exclude_vpc_and_selfpaced_enrollments(request.user)
        courses = []
        for ce in enrollments:
            try:
                course = Course.objects.get(course_id=ce.course_id)
                courses.append(course)
            except:
                # Missing course
                continue

        response = {}
        response['enrollments'] = fill_in_courses(courses, request.user)
        response['status'] = 'success'
        return Response(response)


class Enrollment(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, course_id, format=None):
        """ Enroll in Course """
        user = request.user
        err = {}
        try:
            course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)

            course = course_from_key(course_key)
        except ItemNotFoundError:
            err['err_type'] = 'InvalidCourseId'
            err['err_msg'] = _("Course id is invalid")
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        if not has_access(user, 'enroll', course):
            err['err_type'] = 'InvalidEnrollment'
            err['err_msg'] = _("Enrollment is closed")
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        # see if we have already filled up all allowed enrollments
        is_course_full = CourseEnrollment.is_course_full(course)

        if is_course_full:
            err['err_type'] = 'InvalidEnrollment'
            err['err_msg'] = _("Course is full")
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        # If this course is available in multiple modes, redirect them to a page
        # where they can choose which mode they want.
        available_modes = CourseMode.modes_for_course(course_id)
        available_modes_dict = CourseMode.modes_for_course_dict(course_id, available_modes)
        if CourseMode.has_verified_mode(available_modes_dict):
            err['err_type'] = 'InvalidEnrollment'
            err['err_msg'] = _("Missing course mode")
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        current_mode = available_modes[0]
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        dog_stats_api.increment(
            "common.student.enrollment",
            tags=[u"org:{0}".format(course_key.org),
                  u"course:{0}".format(course_key.course),
                  u"run:{0}".format(course_key.run)]
        )
        server_track(request, 'api.course.enrollment', {
            'username': user.username,
            'course_id': course_id,
        })

        CourseEnrollment.enroll(user, course.id, mode=current_mode.slug)
        return Response()

    def delete(self, request, course_id, format=None):
        """ Unenroll in Course """
        user = request.user
        err = {}
        if not CourseEnrollment.is_enrolled(user, course_id):
            err['err_type'] = 'UserNotEnrolled'
            err['err_msg'] = _("You are not enrolled in this course")
            return Response(err, status=status.HTTP_400_BAD_REQUEST)
        course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        CourseEnrollment.unenroll(user, course_key)
        dog_stats_api.increment(
            "common.student.unenrollment",
            tags=[u"org:{0}".format(course_key.org),
                  u"course:{0}".format(course_key.course),
                  u"run:{0}".format(course_key.run)]
        )
        server_track(request, 'api.course.unenrollment', {
            'username': user.username,
            'course_id': course_id,
        })
        return Response()
