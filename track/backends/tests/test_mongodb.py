from __future__ import absolute_import

from uuid import uuid4

from mock import patch

from django.test import TestCase

from track.backends.mongodb import MongoBackend


class TestMongoBackend(TestCase):
    def setUp(self):
        self.mongo_patcher = patch('track.backends.mongodb.MongoClient')
        self.addCleanup(self.mongo_patcher.stop)
        self.mongo_patcher.start()

        self.backend = MongoBackend()

    def test_mongo_backend(self):
        events = [{'test': 1}, {'test': 2}]

        self.backend.send(events[0])
        self.backend.send(events[1])

        # Check if we inserted events into the database

        calls = self.backend.collection.insert.mock_calls

        self.assertEqual(len(calls), 2)

        # Unpack the arguments and check if the events were used
        # as the first argument to collection.insert

        def first_argument(call):
            _, args, _ = call
            return args[0]

        self.assertEqual(events[0], first_argument(calls[0]))
        self.assertEqual(events[1], first_argument(calls[1]))
