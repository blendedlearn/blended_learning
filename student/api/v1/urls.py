from .category import CategoryList
from .course import (CourseDetail, CoursenameList, CourseSearch,
                     CourseMessage, CourseUpdate, CoursesUpdate, AllCourses, CourseByCategory)
from .enrollment import EnrollmentList, Enrollment
from .feedback import Feedback
from .log import Log
from .register import Register, ResetPassword, Profile
from .synchronize import Synchronize

from django.conf.urls import patterns, url


urlpatterns = patterns('',  # nopep8
    # Register
    url(r'^register/$', Register.as_view()),
    url(r'^passreset/$', ResetPassword.as_view()),
    url(r'^changemessage/$', Profile.as_view()),

    url(r'^enrollments/$', EnrollmentList.as_view()),
    url(r'^category/$', CategoryList.as_view()),
    url(r'^coursename/$', CoursenameList.as_view()),

    # Courseware
    url(r'^courses$', AllCourses.as_view()),
    url(r'^category/(?P<category_id>[^/]*)/courses$',
        CourseByCategory.as_view()),
    url(r'^courseware/$', CourseDetail.as_view()),
    url(r'^courseware/(?P<course_name>.*)$', CourseMessage.as_view()),
    url(r'^notify/$', CoursesUpdate.as_view()),
    url(r'^notify/(?P<course_name>.*)$', CourseUpdate.as_view()),

    # Synchronize
    url(r'^synchronize/$', Synchronize.as_view()),

    # Enrollments
    url(r'^enrollment/(?P<course_id>.*)$',
        Enrollment.as_view()),

    # Log
    url(r'^log/$', Log.as_view()),

    # Search
    url(r'^search$', CourseSearch.as_view()),

    # Feedback
    url(r'^feedback$', Feedback.as_view()),
)
