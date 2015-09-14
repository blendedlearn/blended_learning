# -*- coding: utf-8 -*-
import urllib2
import json
import re
import pytz
from django.conf import settings
from datetime import datetime
from django.utils.timezone import UTC
from django.core.urlresolvers import reverse
from time_utils import time_format

def formatDate(date):
    localtz = pytz.timezone(settings.TIME_ZONE)
    localtime = date.astimezone(localtz)
    return localtime.strftime("%Y年%m月%d日")

def naturalFormatDate(date):
    """nature language interpretation"""
    #根据时间，显示开课时间信息:"即将开课，开课中，几个月前开课"等
    if not date:
        return "即将"

    now = datetime.now(UTC())
    diff = now - date

    # before or after
    if now > date:
        hint = "前"
    else:
        hint = "后"

    diff_days = abs(diff.days)
    if diff_days >= 365:
        return "%d年%s" % (diff_days / 365, hint)
    elif diff_days >= 30:
        return "%d个月%s" % (diff_days / 30, hint)
    elif diff_days >= 7:
        return "%d周%s" % (diff_days / 7, hint)
    elif diff_days >= 1:
        return "%d天%s" % (diff_days, hint)

    diff_seconds = abs(diff.seconds)
    if diff_seconds >= 3600:
        return "%d小时%s" % (diff_seconds / 3600, hint)
    elif diff_seconds >= 60:
        return "%d分钟%s" % (diff_seconds / 60, hint)
    elif diff_seconds >= 1:
        return "%d秒%s" % (diff_seconds, hint)

    return "刚刚"

_knowledgeMap = {
    u"云计算": "cloud",
    u"数据科学": "data",
    u"创业管理": "venture",
}


def translateKnowledgeMap(name):
    return _knowledgeMap.get(name, '')

_levelMap = {
    u"入门": 1,
    u"进阶": 2,
    u"探索": 3,
}


def translateLevel(level):
    return _levelMap.get(level, 0)


def start_status(start, end, now=None):
    """ Return a course start status: pre, ing, post. """
    if not now:
        now = datetime.now(UTC())
    if start is None or now < start:
        return 'pre'
    elif end and end < now:
        return 'post'
    return 'ing'


def enroll_status(start, end, now=None):
    """ Return a course enroll status: pre, ing, post. """
    if not now:
        now = datetime.now(UTC())
    if start and now < start:
        return 'pre'
    elif end and end < now:
        return 'post'
    return 'ing'

def get_course_info(course):
    course_info = {}
    course_info['course_id'] = course.course_id
    course_info['name'] = course.name
    course_info['thumbnail'] = course.thumbnail
    course_info['course_num'] = course.course_num
    course_info['modified'] = naturalFormatDate(course.modified)
    course_info['enrollment'] = ''
    course_info['comment'] = ''
    course_info['subtitle'] = course.subtitle
    course_info['about'] = reverse('about_course', args=[course.course_id])
    course_info['start_time'] = time_format(course.start)
    course_info['end_time'] = time_format(course.end)

    try:
        staff = course.staff.all()[0]
        course_info['staff_avatar'] = staff.avartar
        course_info['staff_name'] = staff.name
        course_info['staff_title'] = "%s %s %s" % (
            staff.company, staff.department, staff.position)
    except:
        course_info['staff_avatar'] = ''
        course_info['staff_name'] = ''
        course_info['staff_title'] = ''

    return course_info