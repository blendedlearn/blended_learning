#!/usr/bin/env python
# coding: utf-8
# "zhoukh"<silegon@gmail.com> 2015-09-17 13:39:17
import json

from course_meta.models_utils import has_course_manage_permission
from course_meta.models import Staff, Course, Classroom,  CourseStaffRelationship

OPERATION_SUCCESS = 1
OPERATION_FAIL = 2

def add_tta_socket(tta_id, ip, port):
    ajax_data = {
        'status' : OPERATION_FAIL,
    }
    tta_socket = tta_socket_create(tta_id, ip, port)
    if isinstance(tta_socket, TtaSocket):
        ajax_data = {
            'status' : OPERATION_SUCCESS,
            'tta_socket_id':tta_socket.pk,
            'tta_socket':tta_socket.ip + ':' + str(tta_socket.port),
            'tta_socket_status':tta_socket.get_status_display(),
        }
    return json.dumps(ajax_data)


def change_course_name(user, course_id, course_name):
    if not has_course_manage_permission(user, course_id):
        ajax_data = {
            'status': OPERATION_FAIL
        }
        return json.dumps(ajax_data)
    course = Course.objects.get(pk=course_id)
    course.name = course_name
    course.save()

    ajax_data = {
        'status': OPERATION_SUCCESS
    }
    return json.dumps(ajax_data)
