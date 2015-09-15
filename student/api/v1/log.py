from rest_framework.response import Response
from rest_framework.views import APIView

import datetime
import logging
import os

log = logging.getLogger(__name__)

LOGSTART = 'start'
LOGEND = '---------------------------7db1c523809b2'

logdir = '/edx/var/log/lms'
logname = 'android'
filename = os.path.join(logdir, logname)

if not os.path.exists(logdir):
    try:
        os.mkdir(logdir)
    except:
        log.error("Permission denied for create %s" % logdir)


class Log(APIView):

    def post(self, request, format=None):
        try:
            content = request.POST.keys()[0]
            # log.info("[android] %s", content)

            with open(filename, 'a') as fh:
                fh.write(content)

            now = datetime.datetime.now()
            destname = filename + '-' + now.strftime('%Y_%m_%d_%H_%M_%S_%f')
            os.rename(filename, destname)
        except Exception, e:
            log.error(e)

        return Response()
