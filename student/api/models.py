# -*- coding: utf-8 -*-
from django.db import models
from jsonfield.fields import JSONField
from django.contrib.auth.models import User
from logging import getLogger

DEFAULT_CHANNEL= 'xuetangx'
log = getLogger(__name__)


class VideoInfo(models.Model):
    """ Cache the video information from 3rd platform """
    vid = models.CharField(max_length=128, db_index=True, unique=True)
    status = models.CharField(max_length=32)
    duration = models.IntegerField()
    image = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return u'[VideoInfo] %s: %s' % (self.vid, self.status)


class HotKeyword(models.Model):
    keyword = models.CharField(max_length=255, db_index=True)
    count = models.IntegerField()

    class Meta:
        ordering = ['-count']


BANNER_TYPE_CHOICES = (
    ('course', 'course'),
    ('category', 'category'),
    ('url', 'url'),
)

BANNER_BELONG_CHOICES = (
    ('mobile', 'mobile'),
    ('tv', 'tv'),
)

BANNER_CHANNEL_CHOICES = (
    ('all', 'all'),
    ('xiaomi', 'xiaomi'),
)

class Banner(models.Model):
    name = models.CharField(max_length=128)
    introduction = models.TextField()
    image = models.CharField(max_length=255, verbose_name='普通尺寸图')
    image_big = models.CharField(max_length=255, default='', blank=True, null=True, verbose_name='大尺寸图(仅tv端)')
    type = models.CharField(max_length=128, default='course', choices=BANNER_TYPE_CHOICES,
                            verbose_name='类型')  # course category url
    order = models.IntegerField(db_index=True, default=0)
    location = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_index=True)
    belong = models.CharField(max_length=10, default='mobile', db_index=True, choices=BANNER_BELONG_CHOICES,
                              verbose_name=u'显示平台')  # 移动端mobile | 电视端tv
    channel = models.CharField(max_length=20, default='all', db_index=True, choices=BANNER_CHANNEL_CHOICES, verbose_name='渠道（小米等）')

    class Meta:
        ordering = ['order']

    def __unicode__(self):
        return u'[Banner] %s: %s' % (self.id, self.name)


class SplashScreen(models.Model):
    screen_id = models.IntegerField()
    period = models.IntegerField(default=1000)
    width = models.IntegerField()
    height = models.IntegerField()
    start = models.DateTimeField()
    end = models.DateTimeField(db_index=True)
    url = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True, db_index=True)
    message = models.CharField(max_length=255)

    def __unicode__(self):
        return u'[SplashScreen] %s: %s' % (self.id, self.screen_id)


class AppVersion(models.Model):
    PLATFORM_CHOICES = (
        ('Android', u'Android'),
        ('iPhone', u'iPhone'),
        ('iPad', u'iPad'),
    )

    platform = models.CharField(max_length=128, choices=PLATFORM_CHOICES, db_index=True)
    channel = models.CharField(max_length=128, default=DEFAULT_CHANNEL, db_index=True)
    version = models.CharField(max_length=128)
    url = models.CharField(max_length=255)
    size = models.CharField(max_length=128)
    description = models.TextField()
    release_date = models.DateTimeField(auto_now=True, db_index=True)

    def __unicode__(self):
        return u'[AppVersion] %s: %s' % (self.platform, self.version)


class LogUploadStrategy(models.Model):
    '''
    移动端日志上传策略, 上传策略可以有多个，选择enabled && updated_at最近的一个
    on_launch -- 是否启动上传
    open_wifi -- 必须是wifi下才上传
    size -- 日志文件大于多少时上传 单位kb
    interval -- 上传时间间隔
    skip_pages -- 哪些页面可以不传
    device -- 设备
    '''
    DEVICE_CHOICES = (
        ('android', u'android'),
        ('ios', u'ios'),
    )
    on_launch = models.BooleanField(default=False, blank=True, verbose_name=u'是否启动上传')
    open_wifi = models.BooleanField(default=False, blank=True, verbose_name=u'必须是wifi下才能上传')
    size = models.CharField(max_length=40, blank=True, verbose_name=u'日志文件大于多少时上传(kb)')
    interval = models.CharField(max_length=40, blank=True, verbose_name=u'上传时间间隔')
    skip_pages = JSONField(default=[], blank=True, verbose_name=u'哪些页面可以不传')
    device = models.CharField(choices=DEVICE_CHOICES, max_length=20, blank=True, verbose_name=u'设备')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=False)


class DeviceInfo(models.Model):
    '''
    uuid -- uuid
    timestamp -- 时间戳
    os -- 设备 android | ios
    brand -- 品牌
    model -- 型号
    imei -- imei
    imsi -- imsi
    os_version -- 操作系统版本
    kernel_version -- 操作系统内核版本
    resolution -- 屏幕宽高
    dpi -- 分辨率
    cpu -- cpu信息
    cpu_frequency -- cpu频率
    cpu_model -- cpu型号
    cpu_cores -- cpu核数
    ram -- 运行内存
    rom -- 机身内存
    app_version -- app版本
    channel -- 渠道
    raw_data -- 原始数据,手机端丢过来的东西都存起来，防止有些字段暂时没有的情况
    '''
    DEVICE_INFO_FILED_MAPPER = {
        'os': 'os', 'brand': 'brand', 'model': 'model',
        'imei': 'imei', 'imsi': 'imsi', 'os_version': 'osVersion',
        'kernel_version': 'kernelVersion', 'resolution': 'resolution',
        'dpi': 'dpi', 'cpu': 'cpu', 'cpu_frequency': 'cpuFrequency',
        'cpu_model': 'cpuModel', 'cpu_cores': 'cpuCores',
        'ram': 'ram', 'rom': 'rom', 'app_version': 'appVersion',
        'channel': 'channel', 'event': 'event',
    }

    uuid = models.CharField(max_length=255, db_index=True, unique=True)
    uid = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.CharField(max_length=255, blank=True)
    os = models.CharField(max_length=255, blank=True)
    brand = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    imei = models.CharField(max_length=30, blank=True)
    imsi = models.CharField(max_length=30, blank=True)
    os_version = models.CharField(max_length=128, blank=True)
    kernel_version = models.CharField(max_length=255, blank=True)
    resolution = models.CharField(max_length=128, blank=True)
    dpi = models.CharField(max_length=128, blank=True)
    cpu = models.CharField(max_length=255, blank=True)
    cpu_frequency = models.CharField(max_length=255, blank=True)
    cpu_model = models.CharField(max_length=255, blank=True)
    cpu_cores = models.CharField(max_length=128, blank=True)
    ram = models.CharField(max_length=128, blank=True)
    rom = models.CharField(max_length=128, blank=True)
    app_version = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=255, blank=True)
    event = models.CharField(default='', max_length=255, blank=True)
    raw_data = JSONField(default={}, verbose_name=u'原始数据')


class IDsInfo(models.Model):
    sid = models.CharField(max_length=255, unique=True)
    uid = models.CharField(max_length=255, blank=True)
    uuid = models.CharField(max_length=255)
    timestamp = models.CharField(max_length=255, blank=True)

    @classmethod
    def new(cls, sid, uid, uuid, timestamp):
        try:
            obj = cls()
            obj.sid = sid
            obj.uid = uid
            obj.uuid = uuid
            obj.timestamp = timestamp
            obj.save()
            return obj
        except:
            log.info('create idsinfo failed: {} {} {} {}'.format(sid, uid, uuid, timestamp))
            return None

class Wisdom(models.Model):
    content = models.TextField(max_length=2048)
    enabled = models.BooleanField(default=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
