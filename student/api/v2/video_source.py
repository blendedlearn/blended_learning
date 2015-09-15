from api.v2.views import APIView
from rest_framework.response import Response
from video.views import get_source


class VideoSourceView(APIView):

    def get(self, request, vid, quality="20", format=None):
        """ Get source url of the cc video, the source url will be changed. 10 is the low quality and 20 is the high quality. """
        result = {
            "sources": get_source(request, vid, int(quality)),
        }
        return Response(result)
