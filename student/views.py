# -*- coding: utf-8 -*-

import time
from datetime import datetime
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
from django_future.csrf import ensure_csrf_cookie, csrf_exempt
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404, HttpResponseRedirect)
from course_meta.models import Staff, Course, Classroom, CourseStaffRelationship
from student.models import UserProfile
from util.json_request import JsonResponse

def index(request):
    context = {"str": "dame"}
    return HttpResponse('templates/index.html', context)

# @ensure_csrf_cookie
def login_user(request):
    #login方法，转接到signin_user方法
    pass


# @ensure_csrf_cookie
def signin_user(request):
    #用户login登录方法
    pass

    # Update login ip in auth_userprofile
    user = request.user
    user_profile = UserProfile.objects.get(user=user)
    user_profile.last_login_ip = request.META.get('REMOTE_ADDR', None)
    user_profile.last_retrievepwd_time = datetime.now(UTC())
    user_profile.save()
    response = JsonResponse({
        'success': True,
        # 'redirect': redirect_url,
        'email': user.email,
        'username': user.username
    })

# @ensure_csrf_cookie
def register_user(request, extra_context=None):
    #用户register注册方法
    if not request.user.is_authenticated():
        return redirect(reverse('login_user'))
    if request.user.is_authenticated():
        return redirect(reverse('dashboard'))

# @ensure_csrf_cookie
def logout_user(request):
    logout(request)
    response = redirect('/')
    # response.delete_cookie('user_id', path='/', domain=settings.SESSION_COOKIE_DOMAIN,)
    return response

# @login_required
def create_classroom(request):
    '''
    :param request: 创建班级的方法
    :return:
    '''
    if request.method == 'GET':
        response = {'err_msg': 'false','message': 'create_classroom'}
        return render_to_response('classroom.html',response)
    else:
        user = request.user.strip()
        try:
            if Staff.objects.filter(user).exists():
                user_role = Staff.objects.get(user).role
                if user_role != 'student':
                    name = request.POST.get('name').strip()
                    classroom = Classroom(name = name)
                    classroom.save()
        except Exception as e:
            message = u'error'
            return HttpResponse(dict(message))

# @login_required
def delete_classroom(requeset):
    '''
    :param requeset: 删除班级的方法
    :return:
    '''
    pass

