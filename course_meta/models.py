# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from collections import defaultdict

from django.db.models import Count
from django.core import cache
from django.utils.timezone import UTC
from django.db import models
from django.dispatch import Signal
from django.conf import settings
from jsonfield.fields import JSONField
from course_meta.utils import start_status, enroll_status
from django.contrib.auth.models import User

log = logging.getLogger(__name__)
try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache

#Signals
send_user_notification = Signal(providing_args=['name','email','state'])

# class Organization(models.Model):
#     """
#     名称:教师组织来源,如某大学
#     数据项:org的英文缩写（便于区分，如tsinghua），组织名称，组织简单介绍
#     """
#     org = models.CharField(max_length=128, db_index=True)
#     name = models.CharField(max_length=255)
#     about = models.TextField()
#
#     def __unicode__(self):
#         return u'%s %s' % (self.org, self.name)

class Staff(models.Model):
    """
    名称:教师数据表,Professors, teachers, TAs, and all these staff are called Staff
    数据项:教师姓名、性别、院校、部职别信息、头像、简介、邮箱
    (因为老师有单独的填写个人信息页面，所以增加此信息，userprofile再存相应的数据)
    """
    user = models.OneToOneField(User, unique=True, db_index=True, related_name='staff')
    name = models.CharField(max_length=255, db_index=True)
    GENDER_CHOICES = (('m', "男"), ('f', "女"))
    gender = models.CharField(
        blank=True, null=True, max_length=6, db_index=True, choices=GENDER_CHOICES
    )
    year_of_birth = models.IntegerField(blank=True, null=True, db_index=True)
    school = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)
    avartar = models.CharField(max_length=255, blank=True)
    about = models.TextField()
    email = models.EmailField(max_length=75, blank=True, null=True)

    @property
    def avatar(self):
        return self.avartar

    @avatar.setter
    def avatar(self, value):
        self.avartar = value

    def __unicode__(self):
        return ' '.join((self.name, self.school, self.department, self.position))

class Course(models.Model):
    """
    名称:课程详情
    数据项:课程名称、学分、章节（记录所有此课程名下的班级开课章节情况）
            缓存项（用于内容扩充的json数据）、课程分类的tag标签
    """
    staff = models.ManyToManyField(Staff, db_index=True,through='CourseStaffRelationship')
    name = models.CharField(max_length=255)
    credit = models.CharField(max_length=128, blank=True)
    chapters = models.TextField(blank=True)
    cached_structure = JSONField(default={}, null=False, blank=True)
    classtag = models.CharField(max_length=255, blank=True, default='')

    def __unicode__(self):
        return u'%s %s' % (self.id, self.name)

    @property
    def start_status(self):
        """ Return the course start status: pre, ing, post. """
        return start_status(self.start, self.end)

    @property
    def enroll_status(self):
        """ Return the course enroll status: pre, ing, post. """
        return enroll_status(self.enrollment_start, self.enrollment_end)

class Classroom(models.Model):
    """
    名称:班级
    数据项:用户，班级名称,班级二维码
    """
    course = models.ForeignKey(Course, db_index=True)
    users = models.ManyToManyField(User, db_index=True)
    name = models.CharField(blank=True, max_length=255,default='')
    bar_code = models.CharField(blank=True, max_length=255,default='')

class CourseStaffRelationship(models.Model):
    """
    名称:教师身份属性与课程管理的关联表，用于记录老师在课程中的身份
    数据项:教师id，课程id，教师身份role
    """
    staff = models.ForeignKey(Staff)
    course = models.ForeignKey(Course)
    roles = ((0, "teacher"),
             (1, "collaborator"),
             (2, "TA"),
             (3, "other"),
             (4, "student"),
             )
    role = models.IntegerField(choices=roles)

    def __unicode__(self):
        return u'%s %s' % (self.course, self.staff)

