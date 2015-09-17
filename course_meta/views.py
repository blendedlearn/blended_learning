# -*- coding: utf-8 -*-
from django.views.decorators.csrf import csrf_exempt

from wechat_sdk import WechatBasic
from wechat_sdk.messages import TextMessage
from wechat_sdk.messages import (
    TextMessage, VoiceMessage, ImageMessage, VideoMessage, LinkMessage, LocationMessage, EventMessage
)
from weixin.weixin import *
from django.conf import settings
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import password_reset_confirm, password_reset_complete
from django.core.cache import cache
from django.core.context_processors import csrf, get_token as csrf_get_token
from django.contrib import messages
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.core.validators import validate_email, validate_slug, ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404, HttpResponseRedirect)
from django.shortcuts import redirect, render_to_response
from django.utils.translation import ungettext
from django.utils.http import cookie_date, base36_to_int
from django.utils.translation import ugettext as _, get_language
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import render_to_response
from django.template import RequestContext

from course_meta.models import Staff, Course, Classroom,  CourseStaffRelationship

from course_meta.models_utils import has_course_manage_permission
from course_meta.ajax_views import change_course_name, change_classroom_name
import json
from types import IntType

@csrf_exempt
def index(request):
    signature = request.GET.get('signature')
    timestamp = request.GET.get('timestamp')
    nonce = request.GET.get('nonce')
    xml = request.body
    body_text = """
        <xml>
        <ToUserName><![CDATA[touser]]></ToUserName>
        <FromUserName><![CDATA[fromuser]]></FromUserName>
        <CreateTime>1405994593</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[新闻]]></Content>
        <MsgId>6038700799783131222</MsgId>
        </xml>
    """
    token = get_weixin_accesstoken()
    # 实例化 wechat
    wechat = WechatBasic(token=token)
    # 对签名进行校验
    if wechat.check_signature(signature=signature, timestamp=timestamp, nonce=nonce):
        # 对 XML 数据进行解析 (必要, 否则不可执行 response_text, response_image 等操作)
        wechat.parse_data(body_text)
        # 获得解析结果, message 为 WechatMessage 对象 (wechat_sdk.messages中定义)
        message = wechat.get_message()

        response = None
        if isinstance(message, TextMessage):
            response = wechat.response_text(content=u'文字信息')
        elif isinstance(message, VoiceMessage):
            response = wechat.response_text(content=u'语音信息')
        elif isinstance(message, ImageMessage):
            response = wechat.response_text(content=u'图片信息')
        elif isinstance(message, VideoMessage):
            response = wechat.response_text(content=u'视频信息')
        elif isinstance(message, LinkMessage):
            response = wechat.response_text(content=u'链接信息')
        elif isinstance(message, LocationMessage):
            response = wechat.response_text(content=u'地理位置信息')
        elif isinstance(message, EventMessage):  # 事件信息
            if message.type == 'subscribe':  # 关注事件(包括普通关注事件和扫描二维码造成的关注事件)
                if message.key and message.ticket:  # 如果 key 和 ticket 均不为空，则是扫描二维码造成的关注事件
                    response = wechat.response_text(content=u'用户尚未关注时的二维码扫描关注事件')
                else:
                    response = wechat.response_text(content=u'普通关注事件')
            elif message.type == 'unsubscribe':
                response = wechat.response_text(content=u'取消关注事件')
            elif message.type == 'scan':
                response = wechat.response_text(content=u'用户已关注时的二维码扫描事件')
            elif message.type == 'location':
                response = wechat.response_text(content=u'上报地理位置事件')
            elif message.type == 'click':
                response = wechat.response_text(content=u'自定义菜单点击事件')
            elif message.type == 'view':
                response = wechat.response_text(content=u'自定义菜单跳转链接事件')
            elif message.type == 'templatesendjobfinish':
                response = wechat.response_text(content=u'模板消息事件')

        # 现在直接将 response 变量内容直接作为 HTTP Response 响应微信服务器即可，此处为了演示返回内容，直接将响应进行输出
        print response
        return render_to_response('index.html',response)

PASSWORD = "no_password"

def teacher_login(request):
    if request.method == "GET":
        return render_to_response('course_meta/teacher_login.html', context_instance=RequestContext(request))
    else:
        username = request.POST['username']
        password = PASSWORD

        user = authenticate(username=username, password=password)
        if user is None:
            user = User.objects.create_user(username, "%s@a.com" % username, password)
            user = authenticate(username=username, password=password)
        login(request, user)
        try:
            staff = Staff.objects.get(user=user)
            return redirect('my_course')
        except:
            staff = Staff(user=user)
            staff.save()
            return redirect('teacher_info')


@login_required(redirect_field_name='teacher_login')
def teacher_info(request, edit=False):
    if request.method == "GET":
        content = {
                "edit":edit,
        }
        if edit:
            user = request.user
            staff = Staff.objects.get(user=user)
            content.update({
                "staff":staff,
            })
        return render_to_response("course_meta/teacher_info.html", content, context_instance=RequestContext(request))
    else:
        user = request.user
        name = request.POST.get("name", None)
        gender = request.POST.get("gender", None)
        year_of_birth = request.POST.get("year_of_birth", None)
        school = request.POST.get("school", None)
        email = request.POST.get("email", None)
        try:
            staff = Staff.objects.get(user=user)
            staff.name = name
            staff.gender = gender
            staff.year_of_birth = int(year_of_birth)
            staff.school = school
            staff.email = email
            staff.save()
        except:
            return redirect('teacher_info')
        return redirect('my_course')

def staff_info(request):
    user = request.user
    staff = Staff.objects.get(user=user)
    content = {
        'staff':staff
    }
    return render_to_response("course_meta/staff_info.html", content, context_instance=RequestContext(request))

@login_required
def my_course(request):
    if request.method == "GET":
        user = request.user
        staff = Staff.objects.get(user=user)
        courses = Course.objects.filter(staff=staff)
        for course in courses:
            course.classrooms = course.classroom_set.all()
        content = {
                "courses":courses,
                "user":user,
                "staff":staff,
        }
        return render_to_response("course_meta/my_course.html", content, context_instance=RequestContext(request))

@login_required
def edit_course(request, course_id):
    if request.method == "GET":
        user = request.user
        try:
            staff = Staff.objects.get(user=user)
            course = Course.objects.get(pk=course_id)
        except:
            #log
            return reverse("my_course")
        course_staff_relationship = CourseStaffRelationship.objects.get(staff=staff, course=course)
        role = course_staff_relationship.role
        if role not in [0,1,2]: # course_meta.course_staff_relationship roles
            #log
            return reverse("my_course")
        course.classrooms = course.classroom_set.all()
        content = {
            "course":course,
            "user":user,
            "staff":staff
        }
        return render_to_response("course_meta/edit_course.html", content, context_instance=RequestContext(request))
    else:
        user = request.user
        if not has_course_manage_permission(user, course_ID):
            return reverse("my_course")

        course_name = request.POST.get("change_course_name", None)
        edit_classroom_name_string = request.POST.get('edit_classroom_name_string', None)
        classroom_name_string = request.POST.get('classroom_name_string', None)

        course.name=change_course_name
        course.save()
        course_staff_relationship = CourseStaffRelationship(course=course,
                staff=staff,
                role=1,       #teacher from course_meta.models.py
        )

        classroom_name_list = classroom_name_string.split(";")
        for classroom_name in classroom_name_list:
            classroom = Classroom(course=course, name=classroom_name)
            classroom.save()

        #edit
        edit_classroom_name_string
        edit_classroom_name_list = edit_classroom_name_string.split(";")
        for edit_classroom_name in edit_classroom_name_list:
            classroom_id, classroom_name = edit_classroom_name_list.split(":")
            classroom = Classroom.objects.get(pk=classroom_id)


        return redirect('my_course')

@login_required
def create_course(request):
    #老师创建课程的方法
    if request.method == "GET":
        content = {}
        return render_to_response("course_meta/create_course.html", content, context_instance=RequestContext(request))
    else:
        user = request.user
        staff = Staff.objects.get(user=user)
        course_name = request.POST.get('course_name', None)
        if not course_name:
            return reverse('my_course')
        classroom_name_string = request.POST.get('classroom_name_string', None)

        course = Course(name=course_name)
        course.save()
        course_staff_relationship = CourseStaffRelationship(course=course,
                staff=staff,
                role=1,       #teacher from course_meta.models.py
        )
        course_staff_relationship.save()

        classroom_name_list = classroom_name_string.split(";")
        for classroom_name in classroom_name_list:
            classroom = Classroom(course=course, name=classroom_name)
            classroom.save()
        return redirect('my_course')


def invite_student(request):
    pass

AJAX_FUNC_DICT = {
    "change_course_name":"change_course_name(user, course_id, course_name)",
    "change_classroom_name":"change_classroom_name(user, classroom_id, classroom_name)",
}


@csrf_exempt
@login_required
def ajax(request):
    user = request.user
    _p = request.POST
    ctype = _p.get("type", None)
    course_id = _p.get("course_id", None)
    course_name = _p.get("course_name", None)
    classroom_id = _p.get("classroom_id", None)
    classroom_name = _p.get("classroom_name", None)
    if not ctype:
        raise Http404
    if ctype in AJAX_FUNC_DICT:
        ajax_data = eval(AJAX_FUNC_DICT[ctype])
        if type(ajax_data) is IntType:
            ajax_data = str(ajax_data)
        #return StreamingHttpResponse(ajax_data)
        return HttpResponse(ajax_data)
    raise Http404
