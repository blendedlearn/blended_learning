# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from django.conf import settings

def time_format(dt, format_string="%Y-%m-%d %H:%M:%S"):
    #时区时间转化方法
    localtz = pytz.timezone(settings.TIME_ZONE)
    try:
        localtime = dt.astimezone(localtz)
        return localtime.strftime(format_string)
    except:
        return ''
