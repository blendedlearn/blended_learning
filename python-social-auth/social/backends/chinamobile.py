#coding=utf8

import logging
import hashlib
import datetime
import requests
import xmltodict
from social.backends.oauth import BaseOAuth1

log = logging.getLogger(__name__)

class ChinaMobileOAuth(BaseOAuth1):

    name = 'chinamobile'

    channel = '1006'
    portal_type = '3'
    author_code = '4esz#EDC'

    EXTRA_DATA = [
        ('nick', 'username'),
        ('sex', 'gender'),
        ('year_of_birth', 'year_of_birth'),
        ('birthday', 'birthday'),
        ('msisdn', 'phone_number'),
        ('headPicUrl', 'profile_image_url'),
    ]

    def get_user_id(self, details, response):
        if response:
            return response['userId']
        return None

    def get_user_details(self, response):
        return response

    def get_current_time(self):
        time = str(datetime.datetime.now())[:23].replace('-','').replace(':','').replace('.','').replace(' ','')
        return time

    def get_md5(self, token, current_time):
        secret = token + self.channel + self.portal_type + current_time + self.author_code
        m = hashlib.md5()
        m.update(secret)
        md5 = m.hexdigest()
        return md5

    def get_user_info(self, token, md5, current_time):
        payload = """
            <Request>
              <tokenId>%s</tokenId>
              <channel>%s</channel>
              <protalType>%s</protalType>
              <time>%s</time>
              <authorCode>%s</authorCode>
            </Request>
        """ % (token, self.channel, self.portal_type, current_time, md5)
        
        try:
            r = requests.post('http://211.140.17.116:8301/opene/api/getUserInfoByToken', data=payload, timeout=5)
            if r.status_code == 200:
                return True, r.content
            else:
                log.error('chinamobile get userinfo http_code:%s' % r.status_code)
                return False, None
        except Exception, e:
            log.error('request to chinamobile to get userinfo failed:%s' % e)
            return False, None

    def process_user_info(self, token, response):
        """
        Get userinfo
        response example:
            <Response>
              <resultCode>1000</resultCode>
              <userInfo>
                <msisdn>18711223344</msisdn>
                <userId>69ed46873fc647a6989f52cd128eee53</userId>
                <nick>和书友41000007121</nick>
                <sex>1</sex>
                <headPicUrl>http://211.140.7.182:9100/client/images/defaulthead.png</headPicUrl>
              </userInfo>
            </Response>
        """
        try:
            result_dict = xmltodict.parse(response)['Response']
            ok = True if result_dict['resultCode'] == '1000' else False
            if result_dict.get('sex'):
                result_dict['sex'] = 'f' if result_dict['sex'] == 0 else 'm'
            if result_dict.get('birthday'):
                birthday = result_dict.get('birthday').split('-')
                if len(birthday) == 3:
                    result_dict['year_of_birth'] = birthday[0] 
        except Exception, e:
            log.error('process chinamobile getUserInfoByToken content failed:%s' % e)
            log.error(response)
            ok = False
        if ok:
            log.info('get chinamobile user info success: token=%s, userId=%s' % (token, result_dict['userInfo']['userId']))
            return ok, result_dict['userInfo']
        else:
            log.error('get chinamobile user info failed:%s' % response)
            return ok, None


    def user_data(self, token, *args, **kwargs):
        current_time = self.get_current_time()
        md5 = self.get_md5(token, current_time)
        ok, content = self.get_user_info(token, md5, current_time)
        if ok:
          return self.process_user_info(token, content)
        else:
          return False, None
        
