from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import json


class Synchronize(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, format=None):
        """
        Arguments:

         - request    : HTTP request
         - course_id  : course id (str: ORG/course/URL_NAME)
         - location   : location of the video at position (str)
         - status     : playing status of the video at position (str)
        Returns:

         - HTTPresponse
        """
        try:
            params = json.loads(request.raw_post_data)
        except:
            params = {}

        return Response(params)
