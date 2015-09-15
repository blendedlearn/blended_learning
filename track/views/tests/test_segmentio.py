"""Ensure we can parse events sent to us from the segment.io webhook integration"""

from datetime import datetime
import json

from ddt import ddt, data, unpack
from mock import sentinel

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.test.utils import override_settings

from track.middleware import TrackMiddleware
from track.tests import EventTrackingTestCase
from track.views import segmentio


SECRET = 'anything'
ENDPOINT = '/segmentio/test/event'
USER_ID = 10

MOBILE_SHIM_PROCESSOR = [
    {
        'ENGINE': 'track.shim.LegacyFieldMappingProcessor'
    },
    {
        'ENGINE': 'track.shim.VideoEventProcessor'
    }
]


def expect_failure_with_message(message):
    """Ensure the test raises an exception and does not emit an event"""
    def test_decorator(func):
        def test_decorated(self, *args, **kwargs):
            self.assertRaisesRegexp(segmentio.EventValidationError, message, func, self, *args, **kwargs)
            self.assert_no_events_emitted()
        return test_decorated
    return test_decorator


@ddt
@override_settings(
    TRACKING_SEGMENTIO_WEBHOOK_SECRET=SECRET,
    TRACKING_IGNORE_URL_PATTERNS=[ENDPOINT],
    TRACKING_SEGMENTIO_ALLOWED_TYPES=['track'],
    TRACKING_SEGMENTIO_DISALLOWED_SUBSTRING_NAMES=['.bi.'],
    TRACKING_SEGMENTIO_SOURCE_MAP={'test-app': 'mobile'},
    EVENT_TRACKING_PROCESSORS=MOBILE_SHIM_PROCESSOR,
)
class SegmentIOTrackingTestCase(EventTrackingTestCase):
    """Test processing of segment.io events"""

    def setUp(self):
        super(SegmentIOTrackingTestCase, self).setUp()
        self.request_factory = RequestFactory()

    def test_get_request(self):
        request = self.request_factory.get(ENDPOINT)
        response = segmentio.segmentio_event(request)
        self.assertEquals(response.status_code, 405)
        self.assert_no_events_emitted()

    @override_settings(
        TRACKING_SEGMENTIO_WEBHOOK_SECRET=None
    )
    def test_no_secret_config(self):
        request = self.request_factory.post(ENDPOINT)
        response = segmentio.segmentio_event(request)
        self.assertEquals(response.status_code, 401)
        self.assert_no_events_emitted()

    def test_no_secret_provided(self):
        request = self.request_factory.post(ENDPOINT)
        response = segmentio.segmentio_event(request)
        self.assertEquals(response.status_code, 401)
        self.assert_no_events_emitted()

    def test_secret_mismatch(self):
        request = self.create_request(key='y')
        response = segmentio.segmentio_event(request)
        self.assertEquals(response.status_code, 401)
        self.assert_no_events_emitted()

    def create_request(self, key=None, **kwargs):
        """Create a fake request that emulates a request from the segment.io servers to ours"""
        if key is None:
            key = SECRET

        request = self.request_factory.post(ENDPOINT + "?key=" + key, **kwargs)
        if 'data' in kwargs:
            request.json = json.loads(kwargs['data'])

        return request

    @data('identify', 'Group', 'Alias', 'Page', 'identify', 'screen')
    @expect_failure_with_message(segmentio.WARNING_IGNORED_TYPE)
    def test_segmentio_ignore_actions(self, action):
        self.post_segmentio_event(action=action)

    @data('edx.bi.some_name', 'EDX.BI.CAPITAL_NAME')
    @expect_failure_with_message(segmentio.WARNING_IGNORED_TYPE)
    def test_segmentio_ignore_names(self, name):
        self.post_segmentio_event(name=name)

    def post_segmentio_event(self, **kwargs):
        """Post a fake segment.io event to the view that processes it"""
        request = self.create_request(
            data=self.create_segmentio_event_json(**kwargs),
            content_type='application/json'
        )
        segmentio.track_segmentio_event(request)

    def create_segmentio_event(self, **kwargs):
        """Populate a fake segment.io event with data of interest"""
        action = kwargs.get('action', 'Track')
        sample_event = {
            "userId": kwargs.get('user_id', USER_ID),
            "event": "Did something",
            "properties": {
                'name': kwargs.get('name', str(sentinel.name)),
                'data': kwargs.get('data', {}),
                'context': {
                    'course_id': kwargs.get('course_id') or '',
                    'app_name': 'edx.mobile.android',
                }
            },
            "channel": 'server',
            "context": {
                "library": {
                    "name": kwargs.get('library_name', 'test-app'),
                    "version": "unknown"
                },
                "app": {
                    "version": "1.0.1",
                },
                'userAgent': str(sentinel.user_agent),
            },
            "receivedAt": "2014-08-27T16:33:39.100Z",
            "timestamp": "2014-08-27T16:33:39.215Z",
            "type": action.lower(),
            "projectId": "u0j33yjkr8",
            "messageId": "qy52hwp4",
            "version": 2,
            "integrations": {},
            "options": {
                "library": "unknown",
                "providers": {}
            },
            "action": action
        }

        if 'context' in kwargs:
            sample_event['properties']['context'].update(kwargs['context'])

        return sample_event

    def create_segmentio_event_json(self, **kwargs):
        """Return a json string containing a fake segment.io event"""
        return json.dumps(self.create_segmentio_event(**kwargs))

    @expect_failure_with_message(segmentio.WARNING_IGNORED_SOURCE)
    def test_segmentio_ignore_unknown_libraries(self):
        self.post_segmentio_event(library_name='foo')

    @expect_failure_with_message(segmentio.ERROR_USER_NOT_EXIST)
    def test_no_user_for_user_id(self):
        self.post_segmentio_event(user_id=40)

    @expect_failure_with_message(segmentio.ERROR_INVALID_USER_ID)
    def test_invalid_user_id(self):
        self.post_segmentio_event(user_id='foobar')

    @data('foo/bar/baz', 'course-v1:foo+bar+baz')
    def test_success(self, course_id):
        middleware = TrackMiddleware()

        request = self.create_request(
            data=self.create_segmentio_event_json(data={'foo': 'bar'}, course_id=course_id),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))

        middleware.process_request(request)
        # The middleware normally emits an event, make sure it doesn't in this case.
        self.assert_no_events_emitted()
        try:
            response = segmentio.segmentio_event(request)
            self.assertEquals(response.status_code, 200)

            expected_event = {
                'username': str(sentinel.username),
                'ip': '',
                'session': '',
                'event_source': 'mobile',
                'event_type': str(sentinel.name),
                'name': str(sentinel.name),
                'event': {'foo': 'bar'},
                'agent': str(sentinel.user_agent),
                'page': None,
                'time': datetime.strptime("2014-08-27T16:33:39.215Z", "%Y-%m-%dT%H:%M:%S.%fZ"),
                'host': 'testserver',
                'context': {
                    'application': {
                        'name': 'edx.mobile.android',
                        'version': '1.0.1',
                    },
                    'user_id': USER_ID,
                    'course_id': course_id,
                    'org_id': 'foo',
                    'path': ENDPOINT,
                    'client': {
                        'library': {
                            'name': 'test-app',
                            'version': 'unknown'
                        },
                        'app': {
                            'version': '1.0.1',
                        },
                    },
                    'received_at': datetime.strptime("2014-08-27T16:33:39.100Z", "%Y-%m-%dT%H:%M:%S.%fZ"),
                },
            }
        finally:
            middleware.process_response(request, None)

        self.assertEquals(self.get_event(), expected_event)

    def test_invalid_course_id(self):
        request = self.create_request(
            data=self.create_segmentio_event_json(course_id='invalid'),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))
        segmentio.track_segmentio_event(request)
        self.assert_events_emitted()

    @expect_failure_with_message(segmentio.ERROR_MISSING_NAME)
    def test_missing_name(self):
        sample_event_raw = self.create_segmentio_event()
        del sample_event_raw['properties']['name']
        request = self.create_request(
            data=json.dumps(sample_event_raw),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))

        segmentio.track_segmentio_event(request)

    @expect_failure_with_message(segmentio.ERROR_MISSING_DATA)
    def test_missing_data(self):
        sample_event_raw = self.create_segmentio_event()
        del sample_event_raw['properties']['data']
        request = self.create_request(
            data=json.dumps(sample_event_raw),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))

        segmentio.track_segmentio_event(request)

    @expect_failure_with_message(segmentio.ERROR_MISSING_TIMESTAMP)
    def test_missing_timestamp(self):
        sample_event_raw = self.create_event_without_fields('timestamp')
        request = self.create_request(
            data=json.dumps(sample_event_raw),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))

        segmentio.track_segmentio_event(request)

    @expect_failure_with_message(segmentio.ERROR_MISSING_RECEIVED_AT)
    def test_missing_received_at(self):
        sample_event_raw = self.create_event_without_fields('receivedAt')
        request = self.create_request(
            data=json.dumps(sample_event_raw),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))

        segmentio.track_segmentio_event(request)

    def create_event_without_fields(self, *fields):
        """Create a fake event and remove some fields from it"""
        event = self.create_segmentio_event()

        for field in fields:
            if field in event:
                del event[field]

        return event

    def test_string_user_id(self):
        User.objects.create(pk=USER_ID, username=str(sentinel.username))
        self.post_segmentio_event(user_id=str(USER_ID))
        self.assert_events_emitted()

    def test_hiding_failure(self):
        sample_event_raw = self.create_event_without_fields('timestamp')
        request = self.create_request(
            data=json.dumps(sample_event_raw),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))

        response = segmentio.segmentio_event(request)
        self.assertEquals(response.status_code, 200)
        self.assert_no_events_emitted()

    @data(
        ('edx.video.played', 'play_video'),
        ('edx.video.paused', 'pause_video'),
        ('edx.video.stopped', 'stop_video'),
        ('edx.video.loaded', 'load_video'),
        ('edx.video.transcript.shown', 'show_transcript'),
        ('edx.video.transcript.hidden', 'hide_transcript'),
    )
    @unpack
    def test_video_event(self, name, event_type):
        course_id = 'foo/bar/baz'
        middleware = TrackMiddleware()

        input_payload = {
            'current_time': 132.134456,
            'module_id': 'i4x://foo/bar/baz/some_module',
            'code': 'mobile'
        }
        if name == 'edx.video.loaded':
            del input_payload['current_time']

        request = self.create_request(
            data=self.create_segmentio_event_json(
                name=name,
                data=input_payload,
                context={
                    'open_in_browser_url': 'https://testserver/courses/foo/bar/baz/courseware/Week_1/Activity/2',
                    'course_id': course_id,
                    'application': {
                        'name': 'edx.mobileapp.android',
                        'version': '29',
                        'component': 'videoplayer'
                    }
                }),
            content_type='application/json'
        )
        User.objects.create(pk=USER_ID, username=str(sentinel.username))

        middleware.process_request(request)
        try:
            response = segmentio.segmentio_event(request)
            self.assertEquals(response.status_code, 200)

            expected_event_without_payload = {
                'username': str(sentinel.username),
                'ip': '',
                'session': '',
                'event_source': 'mobile',
                'event_type': event_type,
                'name': name,
                'agent': str(sentinel.user_agent),
                'page': 'https://testserver/courses/foo/bar/baz/courseware/Week_1/Activity',
                'time': datetime.strptime("2014-08-27T16:33:39.215Z", "%Y-%m-%dT%H:%M:%S.%fZ"),
                'host': 'testserver',
                'context': {
                    'user_id': USER_ID,
                    'course_id': course_id,
                    'org_id': 'foo',
                    'path': ENDPOINT,
                    'client': {
                        'library': {
                            'name': 'test-app',
                            'version': 'unknown'
                        },
                        'app': {
                            'version': '1.0.1',
                        },
                    },
                    'application': {
                        'name': 'edx.mobileapp.android',
                        'version': '29',
                        'component': 'videoplayer'
                    },
                    'received_at': datetime.strptime("2014-08-27T16:33:39.100Z", "%Y-%m-%dT%H:%M:%S.%fZ"),
                },
            }
            expected_payload = {
                'currentTime': 132.134456,
                'id': 'i4x-foo-bar-baz-some_module',
                'code': 'mobile'
            }
            if name == 'edx.video.loaded':
                del expected_payload['currentTime']
        finally:
            middleware.process_response(request, None)

        actual_event = dict(self.get_event())
        payload = json.loads(actual_event.pop('event'))

        self.assertEquals(actual_event, expected_event_without_payload)
        self.assertEquals(payload, expected_payload)
