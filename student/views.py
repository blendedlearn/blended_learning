# -*- coding: utf-8 -*-

import datetime, time
import json
import os
from django.conf import settings
import logging
import re
import urllib
import requests
from collections import defaultdict
from pytz import UTC, timezone

from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import password_reset_confirm, password_reset_complete
from django.core.cache import cache
from django.core.context_processors import csrf, get_token as csrf_get_token
from django.shortcuts import render
from django.views.csrf import ensure_csrf_cookie, csrf_exempt
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404, HttpResponseRedirect)


from course_meta.models import Staff, Course, CourseGroup, CourseCategory, CourseStaffRelationship
@ensure_csrf_cookie
def signin_user(request):
    #login方法
    pass

def register_user(request, extra_context=None):
    #register注册方法
    pass
    if request.user.is_authenticated():
        return redirect(reverse('dashboard'))

def teacher_login(request):
    if request.method == "GET":
        response_dict = {'err_msg': 'false','message': 'request method error, need post'}
        return render_to_response('teacher_login.html',response_dict)
    else:
        unique_code = request.POST.get(unique_code, None)
        if unique_code:
            user_profile, created = UserProfile.objects.get_or_created(unique_code=unique_code)
            if created or not user_profile.name:
                return render_to_response('teacher_info.html')
            else:
                return render_to_response('create_course.html')
        else:
            response_dict = {'err_msg': 'false','message': 'parameter error, need unique_code'}
            return render_to_response('teacher_login.html',response_dict)


@login_required(redirect_field_name='teacher_login')
def teacher_info(request):
    if request.method == "GET":
        response_dict = {'err_msg': 'false','message': 'request method error, need post'}
        return render_to_response('teacher_login.html',response_dict)
    else:
        unique_code = request.POST.get(unique_code, None)
        name = request.POST.get(name, None)
        gender = request.POST.get(gender, None)
        year_of_birth = int(request.POST.get(year_of_birth, None))
        email = request.POST.get(email, None)
        if unique_code:
            user_profile = UserProfile.objects.get(unique_code=unique_code)
            user_profile.name = name
            user_profile.gender = gender
            user_profile.year_of_birth = int(year_of_birth)
            user_profile.email = email
            user_profile.save()
            response_dict = {
            }
            return render_to_response('create_course.html', response_dict)
        else:
            response_dict = {'err_msg': 'false','message': 'parameter error, need unique_code'}
            return render_to_response('teacher_login.html', response_dict)

