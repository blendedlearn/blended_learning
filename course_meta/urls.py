#!/usr/bin/env python
# coding: utf-8
# "zhoukh"<silegon@gmail.com> 2015-09-15 10:07:25

from django.conf.urls import patterns, url, include

urlpatterns = patterns('course_meta.views',
    url(r'^teacher_login$', 'teacher_login', name='teacher_login'),
    url(r'^teacher_info$', 'teacher_info', name='teacher_info'),
    url(r'^edit_teacher_info$', 'teacher_info', {'edit':True}, name='teacher_info'),
    url(r'^my_course$', 'my_course', name="my_course"),
    url(r'^create_course$', 'create_course', name="create_course"),
    #url(r'^finish_course$', 'finish_course'),
    #url(r'^add_class_name$', 'add_class_name'),
    #url(r'^del_class_name$', 'del_class_name'),
    #url(r'^new_course$', 'new_course'),
    #url(r'^choose_class$', 'choose_class'),
    #url(r'^invite_student$', 'invite_student'),
)
