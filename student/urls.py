#!/usr/bin/env python
# coding: utf-8
# "zhoukh"<silegon@gmail.com> 2015-09-15 10:07:25

from django.conf.urls import patterns, url, include

urlpatterns = patterns('student.views',
    url(r'^teacher_login$', 'teacher_login', name='teacher_login'),
    url(r'^teacher_info', 'teacher_info'),
)
