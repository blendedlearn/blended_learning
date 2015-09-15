from django.test import TestCase

from util.email import get_email_domain

class EmailTest(TestCase):
    def test_get_email_domain_qq(self):
        #use qq domain
        email = 'test@qq.com'
        self.assertEqual(get_email_domain(email), 'http://mail.qq.com')

    def test_get_email_domain_gmail(self):
        #use gmail domain
        email = 'test@gmail.com'
        self.assertEqual(get_email_domain(email), 'http://mail.google.com')
