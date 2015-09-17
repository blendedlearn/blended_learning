#!/usr/bin/env python
# coding: utf-8
# "zhoukh"<silegon@gmail.com> 2015-09-17 15:24:42

from student.models import UserProfile

def staff_info_to_userprofile(staff):
    try:
        user_profile = UserProfile()
        user_profile.user = staff.user
        user_profile.name = staff.name
        user_profile.gender = staff.gender
        user_profile.year_of_birth = staff.year_of_birth
        user_profile.school_number = staff.school # TODO
        user_profile.email = staff.email
        user_profile.save()
        return True
    except:
        return False
