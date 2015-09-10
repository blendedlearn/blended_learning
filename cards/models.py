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

log = logging.getLogger(__name__)
try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache

class Collection(models.Model):
    #教师作品集,以一张张的卡片为内容
    title = models.CharField(max_length=255, blank=True, null=True)
    card = models.ForeignKey(Card, db_index=True)

class Card(models.Model):
    #ppt的一张张卡片,3种类型（video，image，problem）
    type = models.CharField(max_length=5, default='image')
    title = models.CharField(max_length=255, blank=True, default='')
    content = JSONField(default={}, null=False, blank=True)
    videoSrc = models.URLField(max_length=255, blank=True, null=True)
    imageSrc = models.ImageField(max_length=255, blank=True, null=True)
    problemSrc =models.CharField(max_length=255, blank=True, null=True)
    audioSrc = models.CharField(max_length=255, blank=True, null=True)

    creator = models.CharField(max_length=255, blank=True)
    pre_editor = models.CharField(max_length=255, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    enrollment_start = models.DateTimeField(null=True, blank=True)
    enrollment_end = models.DateTimeField(null=True, blank=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    pub_status = models.SmallIntegerField(default=0)

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
