"""Event tracker backend that saves events to a python logger and kafka."""

from __future__ import absolute_import

import logging
import json
import traceback

from django.conf import settings

from track.backends import BaseBackend
from track.utils import DateTimeJSONEncoder
import track.kafka.kafka_client as kafka_client

log = logging.getLogger('track.backends.xuetangx_logger')

class XuetangxLoggerBackend(BaseBackend):
    """Event tracker backend that uses a python logger.

        Events are logged to the INFO level as JSON strings.

    """

    def __init__(self,  name,  **kwargs):
        """Event tracker backend that uses a python logger.

            :Parameters:
            - `name`: identifier of the logger,  which should have
            been configured using the default python mechanisms.

        """
        super(XuetangxLoggerBackend,  self).__init__(**kwargs)

        self.event_logger = logging.getLogger(name)

    def send(self,  event):
        event_str = json.dumps(event,  cls=DateTimeJSONEncoder)

        # TODO: remove trucation of the serialized event,  either at a
        # higher level during the emittion of the event,  or by
        # providing warnings when the events exceed certain size.
        event_str = event_str[:settings.TRACK_MAX_EVENT]

        self.event_logger.info(event_str)

        try:
            #obj = XuetangxKafkaClient()
            obj = kafka_client.get_xuetangxkafkaclient_sington()
            obj.ProduceMessage(event_str)
        except:
            self.event_logger.info(traceback.print_exc())