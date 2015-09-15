from api.utils import get_screen_size, get_thumbnail_size
from api.v2.views import APIView
from api.v2.serializer import KnowledgeMapSerializer, KnowledgeMapTagSerializer, CourseSerializer
from course_meta.models import KnowledgeMap, CourseInKnowledgeMap
from rest_framework.response import Response


class KnowledgeMapView(APIView):

    def get(self, request, format=None):
        """ Get the knowledge map list. """
        param = {
            'offset': int(request.GET.get('offset', 0)),
            'limit': int(request.GET.get('limit', 10)),
        }

        query = KnowledgeMap.objects.all()
        total = query.count()
        knowledgemaps = query[param['offset']:param['offset'] + param['limit']]
        result = {
            "knowledgemaps": KnowledgeMapSerializer(knowledgemaps, many=True).data,
            "total": total,
        }
        return Response(result)


class KnowledgeMapTagView(APIView):

    def get(self, request, kid, format=None):
        """ Get all the tags of current knowledge map. """
        knowledgemaptags = CourseInKnowledgeMap.objects.filter(map_id_id=kid)
        result = {
            "tags": KnowledgeMapTagSerializer(knowledgemaptags, many=True).data
        }
        return Response(result)


class KnowledgeMapCourseView(APIView):

    def get(self, request, kid, format=None):
        """ Get the courses of current knowledge map. """

        screen = get_screen_size(request)
        thumbnail_size = get_thumbnail_size(screen, position='list')
        knowledgemaptags = CourseInKnowledgeMap.objects.filter(map_id_id=kid)
        courses = [kt.course_id for kt in knowledgemaptags]
        result = {
            "courses": CourseSerializer(thumbnail_size, courses, many=True).data,
        }
        return Response(result)
