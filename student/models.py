# -*- coding: utf-8 -*-
import hashlib
import json
import uuid
import os
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from random import randrange
from collections import defaultdict
from django.db.models import Q
import pytz
from django.conf import settings
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

from django.db import models
from pytz import UTC
from django.db import models, IntegrityError, transaction
from django.db.models import Count, Q
from django.dispatch import receiver, Signal
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_noop
from django_countries.fields import CountryField
from importlib import import_module
from social_oauth.utils import get_gravatar_url
import logging
from django.utils.translation import ugettext as _
from course_meta.models import Course, Classroom

log = logging.getLogger(__name__)
AUDIT_LOG = logging.getLogger("audit")

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore  # pylint: disable=invalid-name

class UserProfile(models.Model):
    '''
    名称:userprofile，用于存储django.contrib.auth的默认User的辅助信息
    数据项:用户id、名字=昵称、手机号、头像、唯一uuid标识、院校、部职别信息、role身份（用于接收是否是staff的信息)
            出生日期、性别、邮箱、上次登录ip、上次登录时间,meta记录相关扩充的json数据
    '''
    #userprofile存储User的辅助信息
    class Meta:  # pylint: disable=missing-docstring
        db_table = "auth_userprofile"

    user = models.OneToOneField(User, unique=True, db_index=True, related_name='profile')
    name = models.CharField(blank=True, max_length=255, db_index=True)
    nickname = models.CharField(blank=True, max_length=255, db_index=True, default='')
    phone_number = models.CharField(blank=True, null=True, unique=True, max_length=50, db_index=True)
    avatar = models.URLField(blank=True, max_length=255, default='')
    unique_code = models.CharField(blank=True, max_length=20, null=True, unique=True, db_index=True)

    weixin_id = models.CharField(blank=True, max_length=255)
    school = models.CharField(blank=True, max_length=128, default='')
    department = models.CharField(blank=True, max_length=128, default='')
    position = models.CharField(blank=True, max_length=64, default='')
    school_number = models.CharField(blank=True, max_length=64, default='')
    role = models.CharField(blank=True, max_length=64, default='')

    this_year = datetime.now(UTC).year
    VALID_YEARS = range(this_year, this_year - 120, -1)
    year_of_birth = models.IntegerField(blank=True, null=True, db_index=True)
    GENDER_CHOICES = (('m', _('Male')), ('f', _('Female')))
    gender = models.CharField(
        blank=True, null=True, max_length=6, db_index=True, choices=GENDER_CHOICES
    )
    email = models.TextField(blank=True, null=True)
    #数据统计的项目－上次登录的Ip,上次登录的时间
    last_login_ip = models.CharField(max_length=15, blank=True, null=True)
    last_retrievepwd_time = models.DateTimeField(blank=True, null=True)
    meta = models.TextField(blank=True)  # JSON dictionary for future expansion

    def get_meta(self):  # pylint: disable=missing-docstring
        js_str = self.meta
        if not js_str:
            js_str = dict()
        else:
            js_str = json.loads(self.meta)

        return js_str

    def set_meta(self, meta_json):  # pylint: disable=missing-docstring
        self.meta = json.dumps(meta_json)


    @transaction.commit_on_success
    def update_name(self, new_name):
        """Update the user's name, storing the old name in the history.

        Implicitly saves the model.
        If the new name is not the same as the old name, do nothing.

        Arguments:
            new_name (unicode): The new full name for the user.

        Returns:
            None

        """
        if self.name == new_name:
            return

        if self.name:
            meta = self.get_meta()
            if 'old_names' not in meta:
                meta['old_names'] = []
            meta['old_names'].append([self.name, u"", datetime.now(UTC).isoformat()])
            self.set_meta(meta)

        self.name = new_name
        self.save()

    @transaction.commit_on_success
    def update_email(self, new_email):
        """Update the user's email and save the change in the history.

        Implicitly saves the model.
        If the new email is the same as the old email, do not update the history.

        Arguments:
            new_email (unicode): The new email for the user.

        Returns:
            None
        """
        if self.user.email == new_email:
            return

        meta = self.get_meta()
        if 'old_emails' not in meta:
            meta['old_emails'] = []
        meta['old_emails'].append([self.user.email, datetime.now(UTC).isoformat()])
        self.set_meta(meta)
        self.save()

        self.user.email = new_email
        self.user.save()

    def get_unique_code(self):
        '''
        This unique code will replace email to user unique.
        '''
        prefix = self.user.date_joined.strftime('%y%m')
        uid = '{uid:0>8}'.format(uid=self.user.id)
        code = '{}{}'.format(prefix, uid)
        return code

    def get_avatar_url_with_email(self, force_update=False):
        ''''''
        if self.avatar and not force_update:
            return self.avatar
        # TODO: 根据性别完成默认头像
        # default_avatar : https://s.xuetangx.com/files/user/images/.....
        if not self.email:
            return ''
        default_avatar = None
        avatar = get_gravatar_url(self.email, default_avatar=default_avatar)
        return avatar

    @property
    def avatar_url(self):
        if not self.avatar:
            url = os.path.join(settings.PUBLIC_AVATAR_PATH, '{}.png'.format(self.id % 18 + 1))
            return url
        # http开头的都是oauth或者gavater最初得到的
        if self.avatar.startswith('http'):
            return self.avatar
        # 其他都是用户后来上传的
        return os.path.join(settings.PUBLIC_AVATAR_PATH, self.avatar)

    def save(self, *args, **kwargs):
        if not self.unique_code:
            self.unique_code = self.get_unique_code()
        return super(UserProfile, self).save(*args, **kwargs)

    def __unicode__(self):
        nickname = self.nickname if self.nickname else ''
        unique_code = self.unique_code if self.unique_code else ''
        return u'{}:{}'.format(unique_code, nickname)
'''
class ClassroomEnrollment(models.Model):
    """
    名称:用户选课表，记录用户所在班级，学了什么课程
    数据项:用户,课程id，加入课程的时间，
    """
    user = models.ForeignKey(User)
    course = models.ForeignKey(Course, db_index=True)
    classroom = models.ForeignKey(Classroom, db_index=True)
    join_time = models.DateTimeField(auto_now_add=True, null=True, db_index=True)

    class Meta:
        unique_together = (('user', 'course_id'),)
        ordering = ('user', 'course_id')

    def __unicode__(self):
        return (
            "[CourseEnrollment] {}: {} {}"
        ).format(self.user, self.course_id, self.created, self.join_time)

class CourseAccessRole(models.Model):
    """
    名称:课程管理权限表，用于限制用户的管理权限
    数据项:用户、课程id、role身份
    """
    user = models.ForeignKey(User)
    school = models.CharField(max_length=64, db_index=True, blank=True)
    course_id = models.CharField(max_length=255, db_index=True, blank=True)
    role = models.CharField(max_length=64, db_index=True)

    class Meta:  # pylint: disable=missing-docstring
        unique_together = ('user', 'org', 'course_id', 'role')

    @property
    def _key(self):
        """
        convenience function to make eq overrides easier and clearer. arbitrary decision
        that role is primary, followed by org, course, and then user
        """
        return (self.role, self.org, self.course_id, self.user_id)

    def __eq__(self, other):
        """
        Overriding eq b/c the django impl relies on the primary key which requires fetch. sometimes we
        just want to compare roles w/o doing another fetch.
        """
        return type(self) == type(other) and self._key == other._key  # pylint: disable=protected-access

    def __hash__(self):
        return hash(self._key)

    def __lt__(self, other):
        """
        Lexigraphic sort
        """
        return self._key < other._key  # pylint: disable=protected-access

    def __unicode__(self):
        return "[CourseAccessRole] user:{} role:{} org:{} course:{}".format(self.user.username, self.role, self.org, self.course_id)
'''
