"""Map new event context values to old top-level field values. Ensures events can be parsed by legacy parsers."""

import json
import logging

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import UsageKey


log = logging.getLogger(__name__)

CONTEXT_FIELDS_TO_INCLUDE = [
    'username',
    'session',
    'ip',
    'agent',
    'host'
]


class LegacyFieldMappingProcessor(object):
    """Ensures all required fields are included in emitted events"""

    def __call__(self, event):
        context = event.get('context', {})
        if 'context' in event:
            for field in CONTEXT_FIELDS_TO_INCLUDE:
                self.move_from_context(field, event)
            remove_shim_context(event)

        if 'data' in event:
            event['event'] = event['data']
            del event['data']
        else:
            event['event'] = {}

        if 'timestamp' in context:
            event['time'] = context['timestamp']
            del context['timestamp']
        elif 'timestamp' in event:
            event['time'] = event['timestamp']

        if 'timestamp' in event:
            del event['timestamp']

        self.move_from_context('event_type', event, event.get('name', ''))
        self.move_from_context('event_source', event, 'server')
        self.move_from_context('page', event, None)

    def move_from_context(self, field, event, default_value=''):
        """Move a field from the context to the top level of the event."""
        context = event.get('context', {})
        if field in context:
            event[field] = context[field]
            del context[field]
        else:
            event[field] = default_value


def remove_shim_context(event):
    if 'context' in event:
        context = event['context']
        # These fields are present elsewhere in the event at this point
        context_fields_to_remove = set(CONTEXT_FIELDS_TO_INCLUDE)
        # This field is only used for Segment.io web analytics and does not concern researchers
        context_fields_to_remove.add('client_id')
        for field in context_fields_to_remove:
            if field in context:
                del context[field]


NAME_TO_EVENT_TYPE_MAP = {
    'edx.video.played': 'play_video',
    'edx.video.paused': 'pause_video',
    'edx.video.stopped': 'stop_video',
    'edx.video.loaded': 'load_video',
    'edx.video.transcript.shown': 'show_transcript',
    'edx.video.transcript.hidden': 'hide_transcript',
}


class VideoEventProcessor(object):
    """
    Converts new format video events into the legacy video event format.

    Mobile devices cannot actually emit events that exactly match their counterparts emitted by the LMS javascript
    video player. Instead of attempting to get them to do that, we instead insert a shim here that converts the events
    they *can* easily emit and converts them into the legacy format.

    TODO: Remove this shim and perform the conversion as part of some batch canonicalization process.

    """

    def __call__(self, event):
        name = event.get('name')
        if not name:
            return

        if name not in NAME_TO_EVENT_TYPE_MAP:
            return

        event['event_type'] = NAME_TO_EVENT_TYPE_MAP[name]

        if 'event' not in event:
            return

        payload = event['event']

        if 'module_id' in payload:
            module_id = payload['module_id']
            try:
                usage_key = UsageKey.from_string(module_id)
            except InvalidKeyError:
                log.warning('Unable to parse module_id "%s"', module_id, exc_info=True)
            else:
                payload['id'] = usage_key.html_id()

            del payload['module_id']

        if 'current_time' in payload:
            payload['currentTime'] = payload.pop('current_time')

        event['event'] = json.dumps(payload)

        if 'context' not in event:
            return

        context = event['context']

        if 'open_in_browser_url' in context:
            page, _sep, _tail = context.pop('open_in_browser_url').rpartition('/')
            event['page'] = page
