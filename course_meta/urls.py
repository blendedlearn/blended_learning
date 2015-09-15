#!/usr/bin/env python
# coding: utf-8
# "zhoukh"<silegon@gmail.com> 2015-09-15 10:07:25

from django.conf.urls import patterns, url, include

urlpatterns = patterns('course_meta.views',
    (r'^create_course$', 'create_course$'),
    (r'^finish_course$', 'finish_course'),
    (r'^add_class_name$', 'add_class_name'),
    (r'^del_class_name$', 'del_class_name'),
    (r'^new_course$', 'new_course'),
    (r'^choose_class$', 'choose_class'),
    (r'^invite_student$', 'invite_student'),
)
