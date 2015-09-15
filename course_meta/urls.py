#!/usr/bin/env python
# coding: utf-8
# "zhoukh"<silegon@gmail.com> 2015-09-15 10:07:25

from django.conf.urls import patterns, url, include

urlpatterns = patterns('course_meta.views',
    url(r'^create_course$', 'create_course', name="create_course"),
    #url(r'^finish_course$', 'finish_course'),
    #url(r'^add_class_name$', 'add_class_name'),
    #url(r'^del_class_name$', 'del_class_name'),
    #url(r'^new_course$', 'new_course'),
    #url(r'^choose_class$', 'choose_class'),
    #url(r'^invite_student$', 'invite_student'),
)
