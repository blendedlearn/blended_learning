# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from django.conf import settings

import api.v2.category as category
import api.v2.oauth as oauth
import api.v2.course as course
import api.v2.knowledgemap as knowledgemap
import api.v2.search as search
import api.v2.user as user
import api.v2.video_source as video
import api.v2.service as service
import api.v2.logs as logs
import api.v2.device as device
import api.v2.phone as phone
import api.v2.tv as tv


urlpatterns = patterns('',  # nopep8
    # User
    url(r'^user$', user.UserView.as_view(), name='v2_user_register'),
    url(r'^user/password/reset$', user.PasswordResetView.as_view(), name='v2_user_password_reset'),
    url(r'^user/password$', user.PasswordView.as_view(), name='v2_user_change_password'),
    # url(r'^oauth/register/(?P<backend>[^/]+)/$', oauth.OAuthRegisterView.as_view()),
    #url(r'^oauth/login/(?P<backend>[^/]+)/$', oauth.OAuthLoginView.as_view()),
    url(r'^oauth/bind/(?P<provider>[^/]+)$', oauth.OAuthBindView.as_view()),
    url(r'^oauth/unbind/(?P<provider>[^/]+)$', oauth.OAuthUnBindView.as_view()),
    url(r'^oauth/account/status$', oauth.OAuthAccountStatus.as_view()),
    #url(r'^user/email$', View.as_view()),
    url(r'^user/profile$', user.UserProfileView.as_view(), name='v2_user_profile'),
    url(r'^user/realme$', user.UserRealMeView.as_view(), name='v2_user_pwd_check'),

    # Category
    url(r'^categories/?$', category.CategoriesView.as_view(), name='v2_categories'),
    url(r'^category/(?P<cid>[^/]+)/courses/?$',
        category.CategorieCourseView.as_view(), name='v2_get_category_courses'),

    # Knowledge Map
    url(r'^knowledgemaps$', knowledgemap.KnowledgeMapView.as_view(), name='v2_get_knowledgemaps'),
    url(r'^knowledgemap/(?P<kid>[^/]+)/tags$', knowledgemap.KnowledgeMapTagView.as_view(),
        name='v2_get_knowledgemap_tags'),
    url(r'^knowledgemap/(?P<kid>[^/]+)/courses$', knowledgemap.KnowledgeMapCourseView.as_view(),
        name='v2_get_knowledgemap_couses'),

    # Courses
    url(r'^courses/?$', course.CoursesView.as_view(), name='v2_get_courses'),
    url(r'^courses/hot/?$', course.HotCoursesView.as_view(), name='v2_courses_hot'),
    url(r'^courses/recent/?$', course.RecentCoursesView.as_view(), name='v2_courses_recent'),
    url(r'^courses/enroll/?$', course.EnrollCoursesView.as_view(), name='v2_courses_enroll'),
    url(r'^courses/updates/?$', course.CoursesUpdateView.as_view(), name='v2_courses_updates'),
    url(r'^courses/follow/?$', course.FollowCoursesView.as_view(), name='v2_courses_follow'),

    # Course
    # url(r'^course/(?P<course_id>[^/]+/[^/]+/[^/]+)$', course.CourseDetailView.as_view(), name='v2_get_course_details'),
    url(r'^course/{}/?$'.format(settings.COURSE_ID_PATTERN), course.CourseDetailView.as_view(), name='v2_get_course_details'),

    url(r'^course/{}/categories/?$'.format(settings.COURSE_ID_PATTERN), course.CourseCategoryView.as_view(),
        name='v2_get_course_categories'),
    url(r'^course/{}/knowledgemaps$'.format(settings.COURSE_ID_PATTERN), course.CourseKnowledgeMapView.as_view(),
        name='v2_get_course_knowledgemaps'),
    url(r'^course/{}/staffs$'.format(settings.COURSE_ID_PATTERN), course.CourseStaffView.as_view(),
        name='v2_get_course_staffs'),
    url(r'^course/{}/qas$'.format(settings.COURSE_ID_PATTERN), course.CourseQAView.as_view(), name='v2_get_course_qas'),
    url(r'^course/{}/enroll$'.format(settings.COURSE_ID_PATTERN), course.EnrollCourseView.as_view(),
        name='v2_enroll_course'),
    url(r'^course/{}/follow$'.format(settings.COURSE_ID_PATTERN), course.FollowCourseView.as_view(),
        name='v2_fellow_course'),
    url(r'^course/{}/updates$'.format(settings.COURSE_ID_PATTERN), course.CourseUpdateView.as_view(),
        name='v2_get_course_updates'),
    url(r'^course/{}/enrollments$'.format(settings.COURSE_ID_PATTERN), course.CourseEnrollmentsView.as_view(),
        name='v2_get_course_enrollments'),
    url(r'^course/{}/comments$'.format(settings.COURSE_ID_PATTERN), course.CourseCommentsView.as_view(),
        name='v2_get_course_comments'),
    url(r'^course/{}/freqdata$'.format(settings.COURSE_ID_PATTERN), course.CourseFreqDataView.as_view(),
        name='v2_get_course_freqdata'),
    url(r'^course/{}/chapters$'.format(settings.COURSE_ID_PATTERN), course.CourseChaptersView.as_view(),
        name='v2_get_course_chapters'),
    url(r'^course/{}/chapter/(?P<chapter_id>[^/]+)/sequentials$'.format(settings.COURSE_ID_PATTERN),
        course.CourseChapterView.as_view(), name='v2_get_course_chapter_sequentials'),
    url(r'^course/{}/sequential/(?P<sequential_id>[^/]+)/verticals$'.format(settings.COURSE_ID_PATTERN),
        course.CourseSequentialView.as_view(), name='v2_get_course_sequential_verticals'),
    url(r'^course/{}/vertical/(?P<vertical_id>[^/]+)$'.format(settings.COURSE_ID_PATTERN),
        course.CourseVerticalView.as_view(), name='v2_get_course_vertical'),
    # url(r'^course/(?P<course_id>[^/]+/[^/]+/[^/]+)/(?P<category>[^/]+)/(?P<item_id>[^/]+)$', View.as_view()),

    url(r'^course/{}/sync$'.format(settings.COURSE_ID_PATTERN), course.UserCourseStatus.as_view(), name='v2_course_sync'),
    url(r'^courses/sync$', course.UserCoursesStatus.as_view(), name='v2_get_courses_status'),

    url(r'^honors$', course.HonorView.as_view(), name='v2_get_honors'),

    # Organization
    #url(r'^orgs$', View.as_view()),
    #url(r'^org/(?P<oid>[^/]+)$', View.as_view()),
    #url(r'^org/(?P<oid>[^/]+)/staffs$', View.as_view()),
    #url(r'^org/(?P<oid>[^/]+)/courses$', View.as_view()),

    # Video
    url(r'^video/(?P<vid>[^/]+)(/(?P<quality>[^/]+))?$', video.VideoSourceView.as_view(), name='v2_get_video_quality'),

    # Search
    url(r'^search$', search.SearchCourseView.as_view(), name='v2_search'),
    #url(r'^search/hint$', search.SearchHintView.as_view()),
    url(r'^search/hot$', search.SearchHotView.as_view(), name='v2_search_hot'),

    # Banner
    url(r'^banners$', service.BannerView.as_view(), name='v2_get_banners'),

    # Splash Screen
    url(r'^splash-screen$', service.SplashSreenView.as_view(), name='v2_get_splash_screen'),

    # Upgrade
    url(r'^upgrade/(?P<platform>[^/]+)$', service.UpgradeView.as_view(), name='v2_app_upgrade'),

    # Log
    url(r'^logs$', logs.LogsView.as_view(), name='v2_upload_logs'),
    url(r'^logs/(?P<device>[^/]+)/upload_strategy$', logs.LogUploadStrategyView.as_view(),
        name='v2_get_logs_upload_strategy'),

    # device
    url(r'^device$', device.DeviceView.as_view(), name='v2_device_info_upload'),

    # Feedback
    url(r'^feedback$', service.FeedbackView.as_view(), name='v2_feedback'),
    url(r'^bind/email$', user.UserEmailView.as_view(), name='v2_bind_email'),
    url(r'^bind/phone$', user.UserPhoneView.as_view(), name='v2_bin_phone'),
    url(r'^phone/validate$', phone.SMSValidateView.as_view(), name='v2_phone_validate'),
    url(r'^phone/validate/confirm$', phone.SMSValidateConfirmView.as_view(), name='v2_phone_validate_confirm'),

    # Wisdoms for TV
    url(r'^wisdoms/?$', tv.WisdomsView.as_view(), name='v2_get_wisdoms'),
    #
    url(r'^s_log/?$', tv.SimpleLogView.as_view(), name='v2_simple_log'),
    url(r'^heartbeat/?$', service.HeartbeatView.as_view(), name='v2_heartbeat'),

    # 碎片化内容
    url(r'^fragment/hot/?$', course.HotFragmentKnowledgeView.as_view(), name='v2_fragment_knowledge_hot'),
)
