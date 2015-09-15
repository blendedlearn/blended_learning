""" Validators usd to verify the content
"""
import track.views
from dogapi import dog_stats_api
from util.string_utils import string_len

def track_log(request, log_type, event=None, **kwargs):
    """Call dog_stats_api and import track.views.server_track
    """
    dog_stats_api.increment(log_type)
    event = event or {}
    track.views.server_track(request, log_type, event, **kwargs)

def validate_string_length(s, min_len=0, max_len=None):
    """Check whter len(s) in [min_length, max_length]
    min_length = 0, max_length = infinite if undefined

    Return True is valid else False
    """
    if min_len > string_len(s):
        raise ValueError(_('length less than {}').format(min_len))
    if max_len and max_len < string_len(s):
        raise ValueError(_('length more than {}').format(max_len))

def validate_username(s, min_len=2, max_len=30):
    try:
        _validate_string_length(s, min_len, max_len)
    except Exception, e:
        raise ValueError(_('"{field}" must be between {min_len} and {max_len} characters').format(
            field = _('username'), min_len = min_len, max_len = max_len))
    if ALL_NUMBER_RE.match(s):
        raise ValueError(_('"{field}" can NOT contain only numbers(0-9).').format(field = _('username')))
    if not USERNAME_RE.match(s):
        raise ValueError(_("\"{field}\" should only consist of letters (a-z), numbers (0-9), dashes (-), underscores (_)").format(field = _('username')))

def validate_password(pw, repw, min_len=6, max_len=18):
    """Validate password and repassword:
    password and repassword should be same
    call validate_password_complexity() if settings.ENFORCE_PASSWORD_POLICY 
    """
    if pw != repw:
        raise ValueError(_("Enter the password twice to the same"))
    try:
        _validate_string_length(pw, min_len, max_len)
    except Exception, e:
        raise ValueError(_('"{field}" must be between {min_len} and {max_len} characters').format(
            field = _('password'), min_len = min_len, max_len = max_len))

    # Enforce password complexity as an optional feature
    if settings.FEATURES.get('ENFORCE_PASSWORD_POLICY', False):
        try:
            validate_password_length(pw)
            validate_password_complexity(pw)
            validate_password_dictionary(pw)
        except ValidationError, e:
            raise ValueError('{}{}'.format(_('Password: '), '; '.join(e.messages)))
