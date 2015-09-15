from django.contrib.auth.backends import ModelBackend
from student.models import UserProfile
from social_auth.models import UserSocialAuth

class OAuth2Backend(ModelBackend):
    '''
    oauth backend
    '''

    def authenticate(self, provider=None, uid=None):
        try:
            user_social = UserSocialAuth.objects.get(provider=provider, uid=uid)
            return user_social.user
        except UserSocialAuth.DoesNotExist:
            return None


class NickNameBackend(ModelBackend):
    '''
    '''
    def authenticate(self, username=None, password=None, **kwargs):
        if not username:
            return None
        try:
            profile = UserProfile.objects.get(nickname=username)
            user = profile.user
            if user.check_password(password):
                return user
        except UserProfile.DoesNotExist:
            return None
        except Exception:
            return None

class PhoneNumberBackend(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        if not username:
            return None
        try:
            profile = UserProfile.objects.get(phone_number=username)
            user = profile.user
            if user.check_password(password):
                return user
        except UserProfile.DoesNotExist:
            return None
        except Exception:
            return None
