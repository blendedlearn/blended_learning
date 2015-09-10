# -*- coding: utf-8 -*-
# Django settings for blended_learning project.
import sys
import os

from path import path

reload(sys)
sys.setdefaultencoding('utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#set project settings
PROJECT_ROOT = path(__file__).abspath().dirname().dirname()
REPO_ROOT = PROJECT_ROOT.dirname()
COMMON_ROOT = REPO_ROOT / "common"
ENV_ROOT = REPO_ROOT.dirname()  # virtualenv dir /edx-platform is in
COURSES_ROOT = ENV_ROOT / "data"

DATA_DIR = COURSES_ROOT

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'blended_learning',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Asia/Chongqing'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'zh-cn'

# log time format
LOG_TIME_FORMAT = "%Y/%m/%d %H:%M:%S"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Static content
STATIC_ROOT = ENV_ROOT / "staticfiles"

STATICFILES_DIRS = [
    COMMON_ROOT / "static",
    PROJECT_ROOT / "static",
]

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'x7tq6@^+k8l52s)c+y9ueg0!7$4+rh^^x@m#6oi7_m*@sev)c%'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'blended_learning.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'blended_learning.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'south',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.i18n',
    # this is required for admin
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.csrf',

    # Added for django-wiki
    'django.core.context_processors.media',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
)

#######################  oauth  ###################################

AUTHENTICATION_BACKENDS = (
    'social_auth.backends.contrib.douban.Douban2Backend',
    'social_auth.backends.contrib.qq.QQBackend',
    'social_auth.backends.contrib.weibo.WeiboBackend',
    'social_auth.backends.contrib.renren.RenRenBackend',
    'social_auth.backends.contrib.baidu.BaiduBackend',
    'social_auth.backends.contrib.weixin.WeixinBackend',
    'social_auth.backends.contrib.weixin.WeixinAPPBackend',
    'social_auth.backends.contrib.chinamobile.ChinaMobileBackend',
    #'social_oauth.backends.OAuth2Backend',
    # must add，or django default user cant login
    'social_oauth.backends.NickNameBackend',
    'social_oauth.backends.PhoneNumberBackend',
    'django.contrib.auth.backends.ModelBackend',
    # use the ratelimit backend to prevent brute force attacks
    #'ratelimitbackend.backends.RateLimitModelBackend',
    # remove ratelimit for lms
    'rateunlimitbackend.backends.RateUnLimitModelBackend',
)


TEMPLATE_CONTEXT_PROCESSORS += (
    'django.contrib.auth.context_processors.auth',
    # login in htemplate can use "{% url socialauth_begin 'douban-oauth2' %}"
    'social_auth.context_processors.social_auth_by_type_backends',
    'social_auth.context_processors.social_auth_login_redirect',
)


SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.partial.save_status_to_session',
    'social.pipeline.social_auth.save_authentication_user_detail_to_session',
)


SOCIAL_AUTH_DISCONNECT_PIPELINE = (
    # Verifies that the social association can be disconnected from the current
    # user (ensure that the user login mechanism is not compromised by this
    # disconnection).
    'social.pipeline.disconnect.allowed_to_disconnect',
    # Collects the social associations to disconnect.
    'social.pipeline.disconnect.get_entries',
    # Revoke any access_token when possible.
    'social.pipeline.disconnect.revoke_tokens',
    # Removes the social associations.
    'social.pipeline.disconnect.disconnect'
)

SOCIAL_AUTH_LOGIN_URL = '/login-url'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/login-error'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/logged-in'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/new-users-redirect-url'
SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL = '/oauth/newassociation'
SOCIAL_AUTH_BACKEND_ERROR_URL = '/new-error-url'
SOCIAL_AUTH_AUTHENTICATION_SUCCESS_URL = '/oauth/authentication/success'

SOCIAL_AUTH_WEIBO_KEY = '2021069109'
SOCIAL_AUTH_WEIBO_SECRET = '228e875f9f7b1c7d6eb33146cf75ae95'
SOCIAL_AUTH_WEIBO_AUTH_EXTRA_ARGUMENTS = {'forcelogin': 'true'}
SOCIAL_AUTH_WEIBO_FIELDS_STORED_IN_SESSION = ['enrollment_action', 'course_id', 'inviter_id']
SOCIAL_AUTH_QQ_KEY = '101148549'
SOCIAL_AUTH_QQ_SECRET = '9aabfe532957ffdda3e97b894da244c2'
SOCIAL_AUTH_QQ_FIELDS_STORED_IN_SESSION = ['enrollment_action', 'course_id', 'inviter_id']
SOCIAL_AUTH_MOBILE_QQ_OAUTH_CONSUMER_KEY = '1101680520'

SOCIAL_AUTH_DOUBAN_OAUTH2_KEY = '00ef0d07e48eb67a02cd2717adac236e'
SOCIAL_AUTH_DOUBAN_OAUTH2_SECRET = 'a1dd00279d48fa0d'
SOCIAL_AUTH_DOUBAN_FIELDS_STORED_IN_SESSION = ['enrollment_action', 'course_id']

SOCIAL_AUTH_RENREN_KEY = '2697bb7e7461417bb7102049710b39a5'
SOCIAL_AUTH_RENREN_SECRET = 'dbd397d5d74e45069c2a114c4f3b6517'
SOCIAL_AUTH_RENREN_FIELDS_STORED_IN_SESSION = ['enrollment_action', 'course_id']

SOCIAL_AUTH_BAIDU_KEY = 'hj4ghoSGSQobfyGdE9GSHuhO'
SOCIAL_AUTH_BAIDU_SECRET = 'yntelunSKka4VaG4m3wgzoEwYzgujL71'
SOCIAL_AUTH_BAIDU_FIELDS_STORED_IN_SESSION = ['enrollment_action', 'course_id']

SOCIAL_AUTH_WEIXIN_KEY = 'wxccea2c54ef6ceb42'
SOCIAL_AUTH_WEIXIN_SECRET = '8447033b55628e87ed830ef2a246a752'
SOCIAL_AUTH_WEIXIN_SCOPE = ['snsapi_login',]
SOCIAL_AUTH_WEIXIN_FIELDS_STORED_IN_SESSION = ['enrollment_action', 'course_id']

SOCIAL_AUTH_WEIXINAPP_KEY = 'wx33773d39d757855c'
SOCIAL_AUTH_WEIXINAPP_SECRET = 'e6981ac9ec5ad613229eae70a1269478'
SOCIAL_AUTH_WEIXINAPP_SCOPE = ['snsapi_userinfo',]
SOCIAL_AUTH_WEIXINAPP_FIELDS_STORED_IN_SESSION = ['enrollment_action', 'course_id']

#################### cc video ###########################
CC_USERID = "44B36C7761D3412F"
CC_APIKEY = "bySAR5lIFZEx08SKoYLQfNGjZMGx71cQ"
CC_USERID_WM = "33364CBCE093F751"
CC_APIKEY_WM = "EZDEoheXT3REepELsQtwDA3PvZDKEJa3"

#################### static server ###########################
STATIC_SERVER_INTRANET_HOST = 'http://gfsclient.xuetangx.info' # 最后不要有斜线
#STATIC_SERVER_INTRANET_HOST = 'http://10.0.0.113' # 最后不要有斜线
STATIC_SERVER_HOST = 'http://storage.xuetangx.com'
UPLOAD_AVATAR_PATH = os.path.join(STATIC_SERVER_INTRANET_HOST, 'upload/blended_learning/users/info/avatar')
PUBLIC_AVATAR_PATH = os.path.join(STATIC_SERVER_HOST, 'blended_learning/users/info/avatar')
DEFAULT_AVATAR_URL = os.path.join(STATIC_SERVER_HOST, 'xuetangx/users/info/avatar/default.png')