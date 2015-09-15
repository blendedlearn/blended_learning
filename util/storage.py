# -*- encoding: utf-8 -*-
import json
import datetime
import logging
from django.conf import settings
from django.template.defaultfilters import slugify
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2

log = logging.getLogger(__name__)


class SX3(object):
    """
    for xuetangx static file upload to xuetangsx storage
    """

    def __init__(self, sx3=None, public=True):
        """
        initialize xuetangx storage address
        """
        if sx3:
            self.engine = sx3
        else:
            if public:
                self.engine = settings.STATIC_SERVER['PUBLIC_API']
            else:
                self.engine = settings.STATIC_SERVER['INNER_API']

        if not self.engine.startswith("http://"):
            self.engine = "http://" + self.engine


    def upload(self, path, fileobj, do_slugify=True):
        """
        upload a file to sx3 system and return outer visit url

        TODO
            filter fileobj type and exception catch
        """
        register_openers()

        data, headers = multipart_encode({"file": fileobj})

        store_path = self._file_store_path(path, fileobj.name, do_slugify)
        log.info("upload to {}".format(store_path))
        request = urllib2.Request(store_path, data, headers)
        resp = urllib2.urlopen(request)
        if resp.getcode() != 200:
            return (False, )

        respdict = json.loads(resp.read())
        return (respdict["success"], respdict["url"])


    def batch(self, files):
        pass


    def _file_store_path(self, prefix, filename, do_slugify=True):
        if not prefix.endswith("/"):
            prefix += "/"
        if do_slugify:
            path = self.engine + prefix + self.slugify(filename)
        else:
            path = self.engine + prefix + filename
        return path


    def slugify(self, filename):
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        formatted_name = "{}_{}".format(filename, current_time)
        return slugify(formatted_name)
