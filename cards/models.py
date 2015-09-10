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
from course_meta.models import Course

log = logging.getLogger(__name__)
try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache

class Collection(models.Model):
    """
    名称:教师作品集,以一张张的卡片为内容
    数据项:课程id，标题,card,作品集创建者，上次编辑者，创建、更改时间，注册开始结束时间，开始结束时间，发布状态
    """
    course_id = models.ForeignKey(Course, db_index=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    card = models.ManyToManyField(Card, db_index=True)

    creator = models.CharField(max_length=255, blank=True)
    pre_editor = models.CharField(max_length=255, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    enrollment_start = models.DateTimeField(null=True, blank=True)
    enrollment_end = models.DateTimeField(null=True, blank=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    pub_status = models.SmallIntegerField(default=0)

    def __unicode__(self):
        return "[Collection] id: {} course_id: {} title: {} card: {}".format(self.id, self.course_id, self.title, self.card)

class Card(models.Model):
    """
    名称:ppt的一张张卡片,3种内容类型［video，image（可能包含背景录音），problem（可能包含背景录音）］
    数据项:内容类型，名称，json数据串，三种数据的src，背景录音audio的地址
    """
    type = models.CharField(max_length=5, default='image')
    title = models.CharField(max_length=255, blank=True, default='')
    content = JSONField(default={}, null=False, blank=True)
    videoSrc = models.URLField(max_length=255, blank=True, null=True)
    imageSrc = models.ImageField(max_length=255, blank=True, null=True)
    problemSrc =models.CharField(max_length=255, blank=True, null=True)
    audioSrc = models.CharField(max_length=255, blank=True, null=True)

    def __unicode__(self):
        return "[Card] id: {} type: {} title: {} content: {}".format(self.id, self.course_id, self.title, self.content)


class Video(Card):
    objects = VideoManager()
    class Meta:
        proxy = True

class Image(Card):
    objects = ImageManager()
    class Meta:
        proxy = True

class Problem(Card):
    objects = ProblemManager()
    class Meta:
        proxy = True

class VideoManager(models.Manager):
    def get_queryset(self):
        return super(VideoManager, self).get_queryset().filter(type='video')

    def create(self, **kwargs):
        kwargs.update({'type': 'video'})
        return super(VideoManager, self).create(**kwargs)

class ImageManager(models.Manager):
    def get_queryset(self):
        return super(ImageManager, self).get_queryset().filter(type='image')

class ProblemManager(models.Manager):
    def get_queryset(self):
        return super(ImageManager, self).get_queryset().filter(type='problem')

    def create(self, **kwargs):
        kwargs.update({'type': 'problem'})
        return super(VideoManager, self).create(**kwargs)
