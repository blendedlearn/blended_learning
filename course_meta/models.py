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

class CourseGroup(models.Model):
    #课程人员分组
    name = models.CharField(blank=True, max_length=255,default='')
    users = models.ManyToManyField(User, db_index=True, related_name="course_groups")
    course_id = models.CharField(blank=True, max_length=255,default='')
    COHORT = 'cohort'
    GROUP_TYPE_CHOICES = ((COHORT, 'Cohort'),)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES)
    bar_code = models.CharField(blank=True, max_length=255,default='')

class CourseGroupUser(models.Model):
   #用户和CourseGroup的关联表
    courseusergroup_id = models.ManyToManyField(CourseGroup, db_index=True)
    user_id = models.ManyToManyField(User, db_index=True)

class CategoryGroup(models.Model):
    """
    for category management and continuous integration
    """
    active_choices = (
            (1, 'active'),
            (0, 'unactive')
        )
    slug = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=128, blank=True, null=True)
    # is load in search
    active = models.IntegerField(choices=active_choices, db_index=True)
    desp = models.CharField(max_length=255, blank=True, null=True)
    owner = models.CharField(max_length=255, db_index=True)

    def __unicode__(self):
        return u'%s - %s' % (self.name,self.owner)

class CourseCategory(models.Model):
    #课程分类
    parent_id = models.IntegerField(blank=True, null=True)
    slug = models.CharField(max_length=64, blank=True, null=True)
    name = models.CharField(max_length=64)
    cover_image = models.CharField(max_length=255, blank=True, null=True)
    group = models.ForeignKey(CategoryGroup, db_index=True)

    def __unicode__(self):
        return u'%s - %s' % (self.name,self.group)

class Organization(models.Model):
    #教师组织来源,如某大学
    org = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    about = models.TextField()

    def __unicode__(self):
        return u'%s %s' % (self.org, self.name)

class Staff(models.Model):
    #教师,Professors, teachers, TAs, and all these staff are called Staff
    name = models.CharField(max_length=255, db_index=True)
    org_id = models.ForeignKey(Organization, db_index=True)
    company = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)
    avartar = models.CharField(max_length=255, blank=True)
    about = models.TextField()
    mailing_address = models.EmailField(max_length=75, blank=True, null=True)

    @property
    def avatar(self):
        return self.avartar

    @avatar.setter
    def avatar(self, value):
        self.avartar = value

    def __unicode__(self):
        return ' '.join((self.company, self.department, self.position, self.name))

class CourseStaffRelationship(models.Model):
    #教师身份属性
    staff = models.ForeignKey(Staff)
    course = models.ForeignKey(Course)
    roles = ((0, "teacher"),
             (1, "collaborator"),
             (2, "TA"),
             (3, "other"),
             )
    role = models.IntegerField(choices=roles)

    def __unicode__(self):
        return u'%s %s' % (self.course, self.staff)

class Course(models.Model):
    #课程详情
    name = models.CharField(max_length=255)

    subtitle = models.CharField(max_length=512)
    create_time = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    enrollment_start = models.DateTimeField(null=True, blank=True)
    enrollment_end = models.DateTimeField(null=True, blank=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)

    intro_video = models.CharField(max_length=255, blank=True)
    thumbnail = models.CharField(max_length=255)
    cover_compressed = models.IntegerField(max_length=11, default=0)
    video_thumbnail = models.CharField(max_length=255, blank=True)
    effort = models.CharField(max_length=128, blank=True)
    length = models.CharField(max_length=128, blank=True)
    quiz = models.CharField(max_length=128, blank=True)
    prerequisites = models.CharField(max_length=1024)
    about = models.TextField()
    chapters = models.TextField(blank=True)
    serialized = models.SmallIntegerField()
    owner = models.CharField(max_length=64)
    original_url = models.CharField(max_length=255, blank=True)
    category = models.ManyToManyField(CourseCategory, db_index=True)
    staff = models.ManyToManyField(Staff, db_index=True,through='CourseStaffRelationship')

    keywords = models.CharField(max_length=255, blank=True, default='')
    cached_structure = JSONField(default={}, null=False, blank=True)
    open_times = models.IntegerField(max_length=11, default=0, verbose_name='开课次数')
    comment_org = models.CharField(max_length=64, default='')
    comment_course = models.CharField(max_length=64, default='')
    comment_status = models.IntegerField(max_length=4, default=0)
    classtag = models.IntegerField(max_length=11, default=0)

    def __unicode__(self):
        return u'%s %s' % (self.course_id, self.name)

    @property
    def start_status(self):
        """ Return the course start status: pre, ing, post. """
        return start_status(self.start, self.end)

    @property
    def enroll_status(self):
        """ Return the course enroll status: pre, ing, post. """
        return enroll_status(self.enrollment_start, self.enrollment_end)