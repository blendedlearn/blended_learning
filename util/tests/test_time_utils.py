from django.test import TestCase
import pytz
from django.conf import settings
from util.time_utils import time_format
from datetime import datetime
from django.utils.timezone import UTC

class TimeFormatTest(TestCase):
    """
    test util time_format 
    """
    def test_time_format_have_dt(self):
        self.dt_time = datetime.now(UTC())
        #self.dt_time = 'datetime(2015, 4, 22, 8, 21, 11, 910690, tzinfo=<UTC>)'
        response = time_format(self.dt_time)
        self.assertTrue(response)
    
    def test_time_format_no_dt(self):
        self.dt_time = ''
        response = time_format(self.dt_time)
        self.assertFalse(response)
