from django.test import TestCase
from django.test.utils import override_settings
from util.password_policy_validators import (
    validate_password_length, validate_password_complexity,
    validate_password_dictionary
)
from django.core.exceptions import ValidationError
from django.conf import settings

class passwordLengthTest(TestCase):
    """
    test validate password length
    """
    @override_settings(PASSWORD_MIN_LENGTH=1) 
    @override_settings(PASSWORD_MAX_LENGTH=5) 
    def test_validate_password_min_length(self):
        self.password = ''
        with self.assertRaisesRegexp(ValidationError,"[u'Invalid Length (must be 1 characters or more)']"):
            validate_password_length(self.password)
            
    @override_settings(PASSWORD_MAX_LENGTH=5) 
    @override_settings(PASSWORD_MIN_LENGTH=1) 
    def test_validate_password_max_length(self):
        self.password = 'test_password'
        with self.assertRaisesRegexp(ValidationError,"[u'Invalid Length (must be 6 characters or less)']"):
            validate_password_length(self.password)



