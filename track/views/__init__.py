# -*- coding: utf-8 -*-
import datetime

import pytz
import hashlib
from pytz import UTC

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.conf import settings

from django_future.csrf import ensure_csrf_cookie

from edxmako.shortcuts import render_to_response

from track import tracker
from track import contexts
from track import shim
from track.models import TrackingLog
from eventtracking import tracker as eventtracker
from util.time_utils import time_format

# Try to import yajl lib, beacause this lib loads event 2~3 times faster than json lib.
try:
    import yajl as json
except:
    import json

# This is the string that gets returned as a transparent gif.
import base64
beacon_gif = base64.decodestring('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')


def log_event(event):
    """Capture a event by sending it to the register trackers"""
    tracker.send(event)


def _get_request_header(request, header_name, default=''):
    """Helper method to get header values from a request's META dict, if present."""
    if request is not None and hasattr(request, 'META') and header_name in request.META:
        return request.META[header_name]
    else:
        return default


def _get_request_value(request, value_name, default=''):
    """Helper method to get header values from a request's REQUEST dict, if present."""
    if request is not None and hasattr(request, 'REQUEST') and value_name in request.REQUEST:
        return request.REQUEST[value_name]
    else:
        return default


def _get_session_id(request, need_hash=False):
    """ Get session id from request cookie or session. """
    sessionid = request.COOKIES.get('sessionid')
    if not sessionid:
        try:
            sessionid = request.session.session_key
        except:
            pass

    if sessionid and need_hash:
        sessionid = hashlib.md5(sessionid).hexdigest()

    return sessionid


def user_track(request):
    """
    Log when POST call to "event" URL is made by a user. Uses request.REQUEST
    to allow for GET calls.

    GET or POST call should provide "event_type", "event", and "page" arguments.
    """
    # EDXFIX: 参照我们以前的track改，确保track日志一致
    try:  # TODO: Do the same for many of the optional META parameters
        username = request.user.username
    except:
        username = "anonymous"

    sessionid = _get_session_id(request, True)
    event_type = _get_request_value(request, 'event_type')

    if 'event' in request.REQUEST:
        try:
            page = request.REQUEST['page']
            event_obj = request.REQUEST.get('event')
        except:
            page = ''
            event_obj = ''

        try:
            event_obj = json.loads(event_obj)
        except:
            pass
    else:
        page = ''
        try:
            event_obj = json.loads(request.raw_post_data)
            event_type = eventtracker.get_tracker().resolve_context()['path']
        except:
            event_obj = ''

    with eventtracker.get_tracker().context('edx.course.browser', contexts.course_context_from_url(page)):
        event = {
            "username": username,
            "session": sessionid,
            "referer": _get_request_header(request, 'HTTP_REFERER'),
            "origin_referer": request.session.get('referer'),
            "spam": request.COOKIES.get('spam') or request.GET.get('spam'),
            "ip": _get_request_header(request, 'REMOTE_ADDR'),
            "event_source": "browser",
            "event_type": event_type,
            "event": event_obj,
            "agent": _get_request_header(request, 'HTTP_USER_AGENT'),
            "page": page,
            "time": datetime.datetime.now(UTC),
            "host": _get_request_header(request, 'SERVER_NAME'),
            "context": eventtracker.get_tracker().resolve_context(),
        }

    # Some duplicated fields are passed into event-tracking via the context by track.middleware.
    # Remove them from the event here since they are captured elsewhere.
    shim.remove_shim_context(event)

    log_event(event)

    return HttpResponse('success')


def beacon_track(request):
     return HttpResponse(beacon_gif, mimetype='image/gif')


def server_track(request, event_type, event, page=None):
    """
    Log events related to server requests.

    Handle the situation where the request may be NULL, as may happen with management commands.
    """
    if event_type.startswith("/event_logs") and request.user.is_staff:
        return  # don't log

    event = event or {}
    if isinstance(event, dict):
        FILED_MAPPER = {
            'uid': 'HTTP_UID',
            'uuid': 'HTTP_UUID',
            'sid': 'HTTP_SID'
        }
        for key, value in FILED_MAPPER.iteritems():
            _filed = _get_request_header(request, value)
            if _filed:
                event[key] = _filed
            else:
                event[key] = event.get(key) or ''
    
    if event_type.startswith("/analytic_track"):
        event['POST'] = json.loads(request.raw_post_data)

    # request.user is an instance of 
    #    django.contrib.auth.models.User if logged in
    #    django.contrib.auth.models.AnonymousUser if not logged in
    if not request:
        return
    username = request.user.username
    sessionid = _get_session_id(request, True)

    try:
        uid = request.user.id or int(event['uid'])
    except:
        uid = -1

    uuid = event['uuid']

    # define output:
    event = {
        "username": username,
        "uid": uid,
        "uuid": uuid,
        "session": sessionid,
        "referer": _get_request_header(request, 'HTTP_REFERER'),
        "origin_referer": request.session.get('referer'),
        "spam": request.COOKIES.get('spam') or request.GET.get('spam'),
        "ip": _get_request_header(request, 'REMOTE_ADDR'),
        "event_source": "server",
        "event_type": event_type,
        "event": event,
        "agent": _get_request_header(request, 'HTTP_USER_AGENT'),
        "method": request.method,
        "page": page,
        "time": datetime.datetime.now(UTC),
        "host": _get_request_header(request, 'SERVER_NAME'),
        "context": eventtracker.get_tracker().resolve_context(),
    }

    # Some duplicated fields are passed into event-tracking via the context by track.middleware.
    # Remove them from the event here since they are captured elsewhere.
    shim.remove_shim_context(event)

    log_event(event)


def task_track(request_info, task_info, event_type, event, page=None):
    """
    Logs tracking information for events occuring within celery tasks.

    The `event_type` is a string naming the particular event being logged,
    while `event` is a dict containing whatever additional contextual information
    is desired.

    The `request_info` is a dict containing information about the original
    task request.  Relevant keys are `username`, `ip`, `agent`, and `host`.
    While the dict is required, the values in it are not, so that {} can be
    passed in.

    In addition, a `task_info` dict provides more information about the current
    task, to be stored with the `event` dict.  This may also be an empty dict.

    The `page` parameter is optional, and allows the name of the page to
    be provided.
    """

    # supplement event information with additional information
    # about the task in which it is running.
    full_event = dict(event, **task_info)

    # All fields must be specified, in case the tracking information is
    # also saved to the TrackingLog model.  Get values from the task-level
    # information, or just add placeholder values.
    with eventtracker.get_tracker().context('edx.course.task', contexts.course_context_from_url(page)):
        event = {
            "username": request_info.get('username', 'unknown'),
            "ip": request_info.get('ip', 'unknown'),
            "event_source": "task",
            "event_type": event_type,
            "event": full_event,
            "agent": request_info.get('agent', 'unknown'),
            "page": page,
            "time": datetime.datetime.now(UTC),
            "host": request_info.get('host', 'unknown'),
            "context": eventtracker.get_tracker().resolve_context(),
        }

    log_event(event)


@login_required
@ensure_csrf_cookie
def view_tracking_log(request, args=''):
    """View to output contents of TrackingLog model.  For staff use only."""
    if not request.user.is_staff:
        return redirect('/')
    nlen = 100
    username = ''
    if args:
        for arg in args.split('/'):
            if arg.isdigit():
                nlen = int(arg)
            if arg.startswith('username='):
                username = arg[9:]

    record_instances = TrackingLog.objects.all().order_by('-time')
    if username:
        record_instances = record_instances.filter(username=username)
    record_instances = record_instances[0:nlen]

    # fix dtstamp
    fmt = '%a %d-%b-%y %H:%M:%S'  # "%Y-%m-%d %H:%M:%S %Z%z"
    for rinst in record_instances:
        rinst.dtstr = rinst.time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime(fmt)

    return render_to_response('tracking_log.html', {'records': record_instances})
