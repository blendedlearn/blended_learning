# -*- coding: utf-8 -*-
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.core.mail import send_mail


class Feedback(APIView):

    def post(self, request, format=None):
        post_vars = []
        for k, v in request.POST.iteritems():
            post_vars.append("%s: %s," % (k, v))
        content = "\n".join(post_vars)
        if content:
            subject = '来自API v1的用户反馈'
            message = "===== Feedback content =====\nUser: %s\nUserAgent: %s\nPost:\n%s\n===== END =====\n" % (
                request.user, request.META.get('HTTP_USER_AGENT', ''), content)

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                      [settings.API_FEEDBACK_EMAIL], fail_silently=True)

        return Response()
