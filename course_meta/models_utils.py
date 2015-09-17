#!/usr/bin/env python
# coding: utf-8
# "zhoukh"<silegon@gmail.com> 2015-09-17 13:47:09

from course_meta.models import Staff, Course, Classroom,  CourseStaffRelationship

def has_course_manage_permission(user, course_id):
    try:
        staff = Staff.objects.get(user=user)
        course = Course.objects.get(pk=course_id)
    except:
        #log
        return False
    course_staff_relationship = CourseStaffRelationship.objects.get(staff=staff, course=course)
    role = course_staff_relationship.role
    if role not in [0,1,2]: # course_meta.course_staff_relationship roles
        #log
        return False
    return True
