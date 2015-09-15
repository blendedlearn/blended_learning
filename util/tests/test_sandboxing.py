"""
Tests for sandboxing.py in util app
"""

from django.test import TestCase
from util.sandboxing import can_execute_unsafe_code
from django.test.utils import override_settings
from opaque_keys.edx.locations import SlashSeparatedCourseKey


class SandboxingTest(TestCase):
    """
    Test sandbox whitelisting
    """
    @override_settings(COURSES_WITH_UNSAFE_CODE=['edX/full/.*'])
    def test_sandbox_exclusion(self):
        """
        Test to make sure that a non-match returns false
        """
        self.assertFalse(can_execute_unsafe_code(SlashSeparatedCourseKey('edX', 'notful', 'empty')))

    @override_settings(COURSES_WITH_UNSAFE_CODE=['edX/full/.*'])
    def test_sandbox_inclusion(self):
        """
        Test to make sure that a match works across course runs
        """
        self.assertTrue(can_execute_unsafe_code(SlashSeparatedCourseKey('edX', 'full', '2012_Fall')))
        self.assertTrue(can_execute_unsafe_code(SlashSeparatedCourseKey('edX', 'full', '2013_Spring')))

    def test_courses_with_unsafe_code_default(self):
        """
        Test that the default setting for COURSES_WITH_UNSAFE_CODE is an empty setting, e.g. we don't use @override_settings in these tests
        """
        self.assertFalse(can_execute_unsafe_code(SlashSeparatedCourseKey('edX', 'full', '2012_Fall')))
        self.assertFalse(can_execute_unsafe_code(SlashSeparatedCourseKey('edX', 'full', '2013_Spring')))
