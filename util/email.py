# -*- coding: utf-8 -*-

DOMAIN_TRANS_DICT = {
    'gmail.com': 'google.com'
}

def get_email_domain(email):
    suffix = email.split('@')[-1]
    if suffix in DOMAIN_TRANS_DICT:
        suffix = DOMAIN_TRANS_DICT[suffix]
    return 'http://mail.{}'.format(suffix)
