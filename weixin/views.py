# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext, Template
from django.utils.encoding import smart_str, smart_unicode
import hashlib
from xml.etree import ElementTree as etree
from django.shortcuts import render_to_response
from weixin import get_weixin_accesstoken
import requests
import logging
from django.conf import settings

log = logging.getLogger(__name__)

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from django.shortcuts import render
import time

import hashlib

@csrf_exempt
def index(request):
    if request.method=='GET':
        response=HttpResponse(checkSignature(request))
        log.info("response",response)
        # return render_to_response('index.html',response)
        return response
        # return HttpResponse("hello world")
    else:
        xmlstr = smart_str(request.body)
        xml = etree.fromstring(xmlstr)

        ToUserName = xml.find('ToUserName').text
        FromUserName = xml.find('FromUserName').text
        CreateTime = xml.find('CreateTime').text
        MsgType = xml.find('MsgType').text
        Content = xml.find('Content').text
        MsgId = xml.find('MsgId').text
        reply_xml = """<xml>
           <ToUserName><![CDATA[%s]]></ToUserName>
           <FromUserName><![CDATA[%s]]></FromUserName>
           <CreateTime>%s</CreateTime>
           <MsgType><![CDATA[text]]></MsgType>
           <Content><![CDATA[%s]]></Content>
           </xml>"""%(FromUserName,ToUserName,CreateTime,Content + "  Hello world, this is test message")
        return HttpResponse(reply_xml)
        # return HttpResponse('Hello World')

def checkSignature(request):
    signature=request.GET.get('signature',None)
    timestamp=request.GET.get('timestamp',None)
    nonce=request.GET.get('nonce',None)
    echostr=request.GET.get('echostr',None)
    #这里的token我放在setting，可以根据自己需求修改
    access_token = get_weixin_accesstoken()

    tmplist=[access_token,timestamp,nonce]
    tmplist.sort()
    tmpstr="%s%s%s"%tuple(tmplist)
    tmpstr=hashlib.sha1(tmpstr).hexdigest()
    log.info('tmpstr',tmpstr)
    log.info('signature',signature)
    return signature
    # if tmpstr==signature:
    #     return echostr
    # else:
    #     return None