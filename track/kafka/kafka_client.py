"kafka client"

from __future__ import absolute_import
from kafka.client import KafkaClient
from kafka.producer import SimpleProducer
from django.conf import settings

_KAFKA_CLIENT = False

def get_xuetangxkafkaclient_sington():
    global _KAFKA_CLIENT
    if not isinstance(_KAFKA_CLIENT, XuetangxKafkaClient):
        _KAFKA_CLIENT = XuetangxKafkaClient()
    return _KAFKA_CLIENT


class XuetangxKafkaClient(object):
    def __init__(self):
        self.kafka_server = settings.KAFKA_SERVER
        self.topic = settings.KAFKA_TOPIC
        client = KafkaClient(self.kafka_server)
        self.producer = SimpleProducer(client)

    def ProduceMessage(self, strMsg=''):
        res = self.producer.send_messages(self.topic, strMsg)
        return res