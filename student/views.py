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
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.shortcuts import redirect, render_to_response
from django.core.urlresolvers import reverse
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404, HttpResponseRedirect)
from django.template import RequestContext

from course_meta.models import Staff, Course, CourseStaffRelationship
from student.models import UserProfile

@ensure_csrf_cookie
def signin_user(request):
    #login方法
    pass

def register_user(request, extra_context=None):
    #register注册方法
    pass
    if request.user.is_authenticated():
        return redirect(reverse('dashboard'))

PASSWORD = "no_password"

def teacher_login(request):
    if request.method == "GET":
        return render_to_response('student/teacher_login.html', context_instance=RequestContext(request))
    else:
        username = request.POST['username']
        password = PASSWORD

        user = authenticate(username=username, password=password)
        if user is None:
            user = User.objects.create_user(username, "%s@a.com" % username, password)
            user = authenticate(username=username, password=password)
        login(request, user)
        try:
            user_profile = UserProfile.objects.get(user=user)
        except:
            user_profile = UserProfile(user=user)
            user_profile.save()

        if not user_profile.name:
            return redirect('teacher_info')
        else:
            return redirect('create_course')

@login_required(redirect_field_name='teacher_login')
def teacher_info(request):
    if request.method == "GET":
        return render_to_response("student/teacher_info.html", context_instance=RequestContext(request))
    else:
        user = request.user
        name = request.POST.get("real_name", None)
        gender = request.POST.get("gender", None)
        year_of_birth = request.POST.get("year_of_birth", None)
        school_number = request.POST.get("school_number", None)
        email = request.POST.get("email", None)
        try:
            user_profile = UserProfile.objects.get(user=user)
            user_profile.name = name
            user_profile.gender = gender
            user_profile.year_of_birth = int(year_of_birth)
            user_profile.school_number = school_number
            user_profile.email = email
            user_profile.save()
        except:
            return redirect('teacher_info')
        return redirect('create_course')
