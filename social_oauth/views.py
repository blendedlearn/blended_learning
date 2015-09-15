# -*- coding: utf-8 -*-
import logging
import uuid

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

# from django_future.csrf import ensure_csrf_cookie
from social.pipeline.social_auth import social_user
from social_auth.exceptions import NotAllowedToDisconnect
from social_auth.models import UserSocialAuth
from social_auth.views import auth
from social_oauth.utils import (check_can_unbind_social_account, get_strategy,
                                get_uid, get_validate_nickname,
                                new_associate_user)
from student.models import UserProfile
# from student.views import try_change_enrollment, _create_user_invite
from util.json_request import JsonResponse
from django.shortcuts import render_to_response
from social_oauth.utils import PROVIDER_MAPPER, clean_session
from util.validators import track_log, validate_password, validate_username
from course_meta.models import Classroom


logger = logging.getLogger(__name__)


def _new_association(strategy, detail, user, created_on='web_bind'):
    '''
    绑定用户与三方oauth时使用此接口, 返回social_user
    '''
    uid = get_uid(strategy, detail)
    # TODO: AuthAlreadyAssociated
    # 此oauth账号之前已经绑定了学堂在线的账号
    sc_user = new_associate_user(strategy, uid, user, detail,
            created_on=created_on)
    if not sc_user:
        logger.error('new association create social user failed!')
    return sc_user


def new_association(request):
    detail = request.session.get('authentication_user_detail')
    provider = detail['social_provider']
    strategy = get_strategy(provider)
    _new_association(strategy, detail, request.user)
    provider_platform = PROVIDER_MAPPER.get(provider, {}).get('platform', u'三方')
    context = {'provider': provider_platform}
    return render_to_response('oauth/oauth_bind_success.html', context)


def _unbind_social(user, provider):
    # oauth用户默认密码为！，如果没改过密码则此用户不可能通过邮箱
    # 用户名密码的方式登录进来
    # 因为平台逻辑一个用户只能绑定一个平台的一个账号，所以直接查出此用户平台的social_auth删除
    check_can_unbind_social_account(user)
    provider_social = UserSocialAuth.objects.filter(user=user, provider=provider)
    if provider_social.exists():
        provider_social.delete()

@require_POST
@login_required
def unbind_social(request, backend):
    js = {'success': False, 'messages': {}}
    try:
        _unbind_social(request.user, backend)
        js['success'] = True
    except NotAllowedToDisconnect as ex:
        js['messages'][backend] = ex.message
    return JsonResponse(js)


@transaction.commit_on_success
def _get_or_create_oauth_user(strategy, detail, request=None, mobile_client=False, created_on='web'):
    '''
    strategy -- strategy obj
    detail -- oauth登录拿到token时的response
    '''
    backend = strategy.backend
    _created = False
    uid = get_uid(strategy, detail)
    # weibo新接口uid改名叫做id
    if not uid:
        uid = detail.get('id')
    # weixin
    if backend.name in ('weixin', 'weixinapp'):
        weixin_unionid = detail.get('unionid')
        if weixin_unionid:
            weixin_users = UserSocialAuth.objects.filter(weixin_unionid=weixin_unionid).order_by('id')
            weixin_users_count = weixin_users.count()
            # 微信只有一个UserSocialAuth时，使用这个
            if weixin_users_count == 1:
                user = weixin_users[0].user
                user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
                return (user, False)
            elif weixin_users_count > 1:
                # 有web则永远返回第一个web用户
                for each in weixin_users:
                    if each.created_on and each.created_on.startswith('web'):
                        user = each.user
                        user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
                        return (user, False)
                # 否则返回mobile用户
                for each in weixin_users:
                    if each.created_on and each.created_on.startswith('mobile'):
                        user = each.user
                        user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
                        return (user, False)
                # 否则返回weixin app用户(微信服务号活动生成)
                for each in weixin_users:
                    if each.created_on and each.created_on.startswith('app'):
                        user = each.user
                        user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
                        return (user, False)
                # 没有第四种逻辑, 但是还是加上吧
                user = weixin_users[0].user
                user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
                return (user, False)
    if backend.name == 'chinamobile':
        extra_data = backend.extra_data(None, uid, detail, {})
        phone_number = extra_data.get('phone_number', None)
        try:
            user_profile = UserProfile.objects.get(phone_number=phone_number)
            user = user_profile.user
            user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
            return (user, False)
        except:
            pass
    result = social_user(strategy, uid)
    # 已有账户，直接登录
    if result['user']:
        user = result['user']
    # 否则创建用户，之后登录
    else:
        user = User()
        user.username = str(uuid.uuid4()).replace('-', '')[:20]
        user.email = None
        # oauth的自动激活
        user.is_active = True
        user.set_unusable_password()
        user.save()
        extra_data = backend.extra_data(user, uid, detail, {})
        profile = UserProfile(user=user)
        nickname = get_validate_nickname(extra_data['username'])
        oauth_nickname = nickname
        # 重名加后缀，最多尝试10次
        MAX_TRY_TIMES = 10
        while MAX_TRY_TIMES:
            try:
                UserProfile.objects.get(nickname=nickname)
                suffix = str(uuid.uuid4().int)[:6]
                nickname = '{}{}'.format(oauth_nickname, suffix)
                MAX_TRY_TIMES = MAX_TRY_TIMES - 1
            except UserProfile.DoesNotExist:
                break
        profile.phone_number = extra_data.get('phone_number', None)
        profile.nickname = nickname
        profile.unique_code = profile.get_unique_code()
        if request:
            profile.set_register_extra(request=request, cover_data={'channel': backend.name})
        if extra_data.get('profile_image_url'):
            profile.avatar = extra_data['profile_image_url']
        if extra_data.get('gender'):
            profile.gender = extra_data['gender']
        if extra_data.get('year_of_birth'):
            profile.year_of_birth = extra_data['year_of_birth']
        if backend.name == 'chinamobile':
            profile.register_type = 'migu'
            profile.register_auto = 1
        profile.save()
        # TODO: AuthAlreadyAssociated
        # 此oauth账号之前已经绑定了学堂在线的账号
        new_associate_user(strategy, uid, user, detail, created_on=created_on)
        _created = True
        # Track this user register event in oauth
        if not mobile_client:  # do not track api client log 2015.5.26
            event_type = 'weixinapp.user.register_success' if created_on == 'weixinapp' else 'oauth.user.register_success'
            track_log(request, event_type, {
                'success': True,
                'uid': user.id,
                'provider': backend.name,
            })
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
    return (user, _created)

# @ensure_csrf_cookie
def authentication_success(request):
    '''
    新用户注册时
    用户直接走oauth后通过python-social-auth的auth后，成功会回调到此处，
    此时django的用户应该是未登录状态 request.user.is_authenticated() is False
    '''
    detail = request.session.get('authentication_user_detail')
    # inviter_id = request.session.get('inviter_id')
    provider = detail['social_provider']
    strategy = get_strategy(provider)
    enrollment_action = request.session.get('enrollment_action')
    classroom_id = request.session.get('classroom_id')
    user, _created = _get_or_create_oauth_user(strategy, detail, request)
    # # 如果有邀请
    # if inviter_id:
    #     _create_user_invite(inviter_id, user)
    login(request, user)
    user_profile = user.profile
    user_profile.last_login_ip = request.META.get('REMOTE_ADDR', None)
    user_profile.save()
    # 如果用户没有登录就选课，并且这时候选择的是oauth，尝试enroll课程
    if enrollment_action:
        request.method = 'POST'
        request.POST = request.POST.copy()
        request.POST['enrollment_action'] = enrollment_action
        request.POST['classroom_id'] = classroom_id

        classroom = Classroom.objects.get(id = classroom_id)
        classroom.user = request.user
        classroom.save()
        # try_change_enrollment(request)
    next_url = request.session.get('next', '')
    context = {'next': next_url}    

    track_log(request, 'oauth.user.login_success', {
        'success': True,
        'uid': user.id,
        'provider': strategy.backend.name,
    })
    return render_to_response('oauth/oauth_login_success.html', context)


@clean_session(['next', 'enrollment_action', 'course_id'])
def oauth_login(request, backend):
    '''
    注册和登录时都不应该是登录后的状态
    '''
    context = {'next': request.session.get('next', '')}
    if request.user.is_authenticated():
        return render_to_response('oauth/oauth_login_success.html', context)
    #TODO: oauth登录失败的处理, 跳转到oauth失败的页面
    return auth(request, backend)


@clean_session(['next', 'enrollment_action', 'course_id'])
def oauth_register(request, backend):
    '''
    注册和登录时都不应该是登录后的状态
    '''
    context = {'next': request.session.get('next', '')}
    if request.user.is_authenticated():
        return render_to_response('oauth/oauth_login_success.html', context)
    return auth(request, backend)

@clean_session(['next',])
@login_required
def oauth_bind(request, backend):
    '''
    绑定时需要时登录状态
    '''
    return auth(request, backend)
