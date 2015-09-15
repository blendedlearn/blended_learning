from course_meta.models import CourseCategory
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class CategoryList(APIView):

    def get(self, request, format=None):
        response = {
            'category': [],
            'status': 'success'
        }

        categorys = CourseCategory.objects.all()
        for category in categorys:
            category_dict = {}
            category_dict['id'] = category.id
            category_dict['display_name'] = category.name
            response['category'].append(category_dict)

        return Response(response)
