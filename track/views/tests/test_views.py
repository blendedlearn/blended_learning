# pylint: disable=missing-docstring,maybe-no-member

from track import views
from track.middleware import TrackMiddleware
from mock import patch, sentinel
from freezegun import freeze_time
from django.contrib.auth.models import AnonymousUser

from django.test import TestCase
from django.test.client import RequestFactory
from django.conf import settings

from eventtracking import tracker

from util.time_utils import time_format
from datetime import datetime

expected_time = datetime(2013, 10, 3, 8, 24, 55)
#expected_time = time_format(datetime(2013, 10, 3, 8, 24, 55), settings.LOG_TIME_FORMAT)

class TestTrackViews(TestCase):

    def setUp(self):
        self.request_factory = RequestFactory()
        self.user = AnonymousUser()

        patcher = patch('track.views.tracker')
        self.mock_tracker = patcher.start()
        self.addCleanup(patcher.stop)

        self.path_with_course = '/courses/foo/bar/baz/xmod/'
        self.url_with_course = 'http://www.edx.org' + self.path_with_course

        self.event = {
            sentinel.key: sentinel.value
        }

    @freeze_time(expected_time)
    def test_user_track(self):
        request = self.request_factory.get('/event', {
            'page': self.url_with_course,
            'event_type': sentinel.event_type,
            'event': {}
        })
        request.user = self.user
        request.session = {"referer": "www.baidu.com"}
        with tracker.get_tracker().context('edx.request', {'session': sentinel.session}):
            views.user_track(request)

        expected_event = {
            'username': '',
            'session': None,
            'ip': '127.0.0.1',
            'event_source': 'browser',
            'event_type': u'sentinel.event_type',
            'event': {},
            'agent': '',
            'page': unicode(self.url_with_course),
            'time': '2013/10/03 16:24:55',
            'host': 'testserver',
            'referer': '',
            'origin_referer': 'www.baidu.com',
            'spam': None,
            'context': {
                'course_id': u'foo/bar/baz',
                'org_id': u'foo',
            }
        }
        self.mock_tracker.send.assert_called_once_with(expected_event)

    @freeze_time(expected_time)
    def test_user_track_with_missing_values(self):
        request = self.request_factory.get('/event')
        request.session = {"referer": "www.baidu.com"}
        with tracker.get_tracker().context('edx.request', {'session': sentinel.session}):
            views.user_track(request)

        expected_event = {
            'username': 'anonymous',
            'session': None,
            'ip': '127.0.0.1',
            'event_source': 'browser',
            'event_type': '',
            'event': '',
            'agent': '',
            'page': '',
            'time': '2013/10/03 16:24:55',
            'referer': '',
            'origin_referer': 'www.baidu.com',
            'spam': None,
            'host': 'testserver',
            'context': {
                'course_id': '',
                'org_id': '',
            },
        }
        self.mock_tracker.send.assert_called_once_with(expected_event)

    @freeze_time(expected_time)
    def test_user_track_with_middleware(self):
        middleware = TrackMiddleware()
        request = self.request_factory.get('/event', {
            'page': self.url_with_course,
            'event_type': sentinel.event_type,
            'event': {}
        })
        request.user = self.user
        request.session = {"referer": "www.baidu.com"}
        middleware.process_request(request)
        try:
            views.user_track(request)

            expected_event = {
                'username': '',
                'session': None,
                'ip': '127.0.0.1',
                'event_source': 'browser',
                'event_type': str(sentinel.event_type),
                'event': {},
                'agent': '',
                'page': self.url_with_course,
                'time': '2013/10/03 16:24:55',
                'host': 'testserver',
                'spam': None,
                'referer': '',
                'origin_referer': 'www.baidu.com',
                'context': {
                    'course_id': 'foo/bar/baz',
                    'org_id': 'foo',
                    'user_id': '',
                    'path': u'/event'
                },
            }
        finally:
            middleware.process_response(request, None)

        self.mock_tracker.send.assert_called_once_with(expected_event)

    @freeze_time(expected_time)
    def test_server_track(self):
        request = self.request_factory.get(self.path_with_course)
        request.user = self.user
        request.session = {"referer": "www.baidu.com"}
        views.server_track(request, str(sentinel.event_type), '{}')

        '''
        expected_event = {
            'username': 'anonymous',
            'ip': '127.0.0.1',
            'event_source': 'server',
            'event_type': str(sentinel.event_type),
            'event': '{}',
            'agent': '',
            'page': None,
            'time': expected_time,
            'host': 'testserver',
            'context': {},
        }
        '''
        expected_event = {
            'username': '',
            'ip': '127.0.0.1',
            'event_source': 'server',
            'event_type': str(sentinel.event_type),
            'event': '{}',
            'agent': '',
            'page': None,
            'time': '2013/10/03 16:24:55',
            'host': 'testserver',
            'context': {},
            'method': "GET",
            'session': None,
            'referer': '',
            'origin_referer':'www.baidu.com',
            'event_source': 'server',
            'spam':None
        }
        self.mock_tracker.send.assert_called_once_with(expected_event)

    @freeze_time(expected_time)
    def test_server_track_with_middleware(self):
        middleware = TrackMiddleware()
        request = self.request_factory.get(self.path_with_course)
        request.user = self.user
        request.session = {"referer": "www.baidu.com"}
        middleware.process_request(request)
        # The middleware emits an event, reset the mock to ignore it since we aren't testing that feature.
        self.mock_tracker.reset_mock()
        try:
            views.server_track(request, str(sentinel.event_type), '{}')

            expected_event = {
                'username': '',
                'ip': '127.0.0.1',
                'event_source': 'server',
                'event_type': str(sentinel.event_type),
                'event': '{}',
                'agent': '',
                'page': None,
                'time': '2013/10/03 16:24:55',
                'host': 'testserver',
                'session': None,
                'referer': '',
                'spam': None,
                'method': "GET",
                'origin_referer': 'www.baidu.com',
                'context': {
                    'user_id': '',
                    'course_id': u'foo/bar/baz',
                    'org_id': 'foo',
                    'path': u'/courses/foo/bar/baz/xmod/'
                },
            }
        finally:
            middleware.process_response(request, None)

        self.mock_tracker.send.assert_called_once_with(expected_event)

    @freeze_time(expected_time)
    def test_server_track_with_middleware_and_google_analytics_cookie(self):
        middleware = TrackMiddleware()
        request = self.request_factory.get(self.path_with_course)
        request.COOKIES['_ga'] = 'GA1.2.1033501218.1368477899'
        request.user = self.user
        request.session = {"referer": "www.baidu.com"}
        middleware.process_request(request)
        # The middleware emits an event, reset the mock to ignore it since we aren't testing that feature.
        self.mock_tracker.reset_mock()
        try:
            views.server_track(request, str(sentinel.event_type), '{}')

            expected_event = {
                'username': '',
                'ip': '127.0.0.1',
                'event_source': 'server',
                'event_type': str(sentinel.event_type),
                'event': '{}',
                'agent': '',
                'page': None,
                'time': '2013/10/03 16:24:55',
                'host': 'testserver',
                'session': None,
                'referer': '',
                'origin_referer': 'www.baidu.com',
                'spam': None,
                'method': 'GET',
                'context': {
                    'user_id': '',
                    'course_id': u'foo/bar/baz',
                    'org_id': 'foo',
                    'path': u'/courses/foo/bar/baz/xmod/'
                },
            }
        finally:
            middleware.process_response(request, None)

        self.mock_tracker.send.assert_called_once_with(expected_event)

    @freeze_time(expected_time)
    def test_server_track_with_no_request(self):
        request = None
        views.server_track(request, str(sentinel.event_type), '{}')

        expected_event = {
            'username': 'anonymous',
            'ip': '',
            'event_source': 'server',
            'event_type': str(sentinel.event_type),
            'event': '{}',
            'agent': '',
            'page': None,
            'time': expected_time,
            'host': '',
            'context': {},
        }
        #self.mock_tracker.send.assert_called_once_with(expected_event)

    @freeze_time(expected_time)
    def test_task_track(self):
        request_info = {
            'username': 'anonymous',
            'ip': '127.0.0.1',
            'agent': 'agent',
            'host': 'testserver',
        }

        task_info = {
            sentinel.task_key: sentinel.task_value
        }
        expected_event_data = dict(task_info)
        expected_event_data.update(self.event)

        views.task_track(request_info, task_info, str(sentinel.event_type), self.event)

        expected_event = {
            'username': 'anonymous',
            'ip': '127.0.0.1',
            'event_source': 'task',
            'event_type': str(sentinel.event_type),
            'event': expected_event_data,
            'agent': 'agent',
            'page': None,
            'time': '2013/10/03 16:24:55',
            'host': 'testserver',
            'context': {
                'course_id': '',
                'org_id': ''
            },
            }
        self.mock_tracker.send.assert_called_once_with(expected_event)
