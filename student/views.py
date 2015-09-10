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