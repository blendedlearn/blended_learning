import json
import re

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.validators import (validate_email, validate_slug,
                                    ValidationError)
from django.http import HttpResponse
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from student.forms import PasswordResetFormNoActive
from student.models import UserProfile
from student.views import _do_create_account
from track.views import server_track
from util.string_utils import string_len

ALL_NUMBER_RE = re.compile(r'^\d+$')
USERNAME_RE = re.compile(u'^[\u4e00-\u9fa5-\w]+$')

class Register(APIView):

    def post(self, request, format=None):
        post_vars = json.loads(request.POST.keys()[0])
        required_post_vars = ['email', 'username', 'password']
        err = {}

        # Confirm we have a properly formed request
        for k in required_post_vars:
            if k not in post_vars:
                err['err_type'] = 'MissingParameter'
                err['err_msg'] = "Missing Parameter %s" % k
                return Response(err, status=status.HTTP_400_BAD_REQUEST)

        # Check paremeters
        for k in required_post_vars:
            if len(post_vars[k]) < 2:
                error_str = {
                    'username': _('Username must be minimum of two characters long.'),
                    'email': _('A properly formatted e-mail is required.'),
                    'password': _('A valid password is required.')
                }
                err['err_type'] = 'InvalidParameter'
                err['err_msg'] = error_str[k]
                return Response(err, status=status.HTTP_400_BAD_REQUEST)

        # Validate email
        try:
            validate_email(post_vars['email'])
        except ValidationError:
            err['err_type'] = 'InvalidParameter'
            err['err_msg'] = _("Valid e-mail is required.")
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        # Validate username
        if string_len(post_vars['username']) > 16:
            error_str = {
                'username': _('Username must be maximum of eight characters long.'),
            }
            err['err_type'] = 'InvalidParameter'
            err['err_msg'] = error_str['username']
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        if ALL_NUMBER_RE.match(post_vars['username']):
            err['err_type'] = 'InvalidParameter'
            err['err_msg'] = _('Username cannot be all Numbers.')
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        if not USERNAME_RE.match(post_vars['username']):
            err['err_type'] = 'InvalidParameter'
            err['err_msg'] = _('Username should only consist of A-Z and 0-9 and chinese character and "_" and "-", with no spaces.')
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        # Ok, looks like everything is legit.  Create the account.
        post_vars['name'] = ''
        ret = _do_create_account(post_vars, True, request=request)
        # if there was an error then return that
        if isinstance(ret, HttpResponse):
            json_obj = json.loads(ret.content)
            err['err_type'] = '%sAlreadyExists' % json_obj.get('field').capitalize()
            err['err_msg'] = json_obj.get('value')
            return Response(err, status=status.HTTP_400_BAD_REQUEST)

        user, profile, registration = ret

        server_track(request, 'api.user.register', {
            'uid': user.id,
            'username': user.username,
        })
        return Response()


class ResetPassword(APIView):

    def post(self, request, format=None):
        """ Reset password """
        form = PasswordResetFormNoActive(request.POST)
        if form.is_valid():
            form.save(use_https=request.is_secure(),
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      request=request,
                      domain_override=request.get_host())
            return Response({'success': True})
        else:
            return Response({'success': False, 'error': _('Invalid e-mail')}, status=status.HTTP_400_BAD_REQUEST)


class Profile(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        """ Get user profile"""
        profile = UserProfile.objects.get(user=request.user)

        def get_default(attr, default=''):
            return attr if attr else default
        result = {
            'username': request.user.profile.nickname,
            'full_name': profile.name,
            'email': get_default(request.user.email),
            'gender': get_default(profile.gender),
            'year_of_birth': get_default(profile.year_of_birth),
            'level_of_education': get_default(profile.level_of_education),
            'goals': get_default(profile.goals),
        }
        return Response(result)

    def post(self, request, format=None):
        """ Edit user profile """
        profile = UserProfile.objects.get(user=request.user)
        parameters = json.loads(request.POST.keys()[0])

        # Check password
        user = authenticate(username=request.user.username,
                            password=parameters.get('password'))
        if user:
            if parameters.get('new_password'):
                user.set_password(parameters['new_password'])
                user.save()

            if parameters.get('gender'):
                profile['gender'] = parameters['gender']
            if parameters.get('year_of_birth'):
                profile['year_of_birth'] = parameters['year_of_birth']
            if parameters.get('level_of_education'):
                profile['level_of_education'] = parameters[
                    'level_of_education']
            if parameters.get('goals'):
                profile['goals'] = parameters['goals']

            profile.save()
            return Response()
        else:
            err = {}
            err['err_type'] = 'Wrong password'
            err['err_msg'] = 'Wrong password'
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
