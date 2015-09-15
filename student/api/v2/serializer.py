# -*- coding: utf-8 -*-

import logging
import re
import requests

from django.core import cache
from django.conf import settings
from django.core.urlresolvers import reverse
from HTMLParser import HTMLParser
from rest_framework import serializers
from rest_framework import status
from opaque_keys.edx.keys import CourseKey

from api.models import Banner, SplashScreen, AppVersion, Wisdom
from api.models import VideoInfo, LogUploadStrategy, DeviceInfo
from comment.models import Comment
from course_meta.models import (
    Course, CourseCategory, Staff, KnowledgeMap,
    Organization, CourseInKnowledgeMap, CourseQA,
    FragmentKnowledge)
from video.views import get_video_info
from course_modes.models import CourseMode
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from opaque_keys.edx.locator import AssetLocator
from course_stat import stat as course_stat

log = logging.getLogger(__name__)

CHAPTER_NUM_RE = re.compile('\d+')
_datetime_format = "%Y-%m-%d %H:%M:%S"

# If we can't find a 'general' CACHE defined in settings.py, we simply fall back
# to returning the default cache. This will happen with dev machines.
try:
    cache = cache.get_cache('general')
except Exception:
    cache = cache.cache


class CategorySerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField("get_cover_image")
    parent_id = serializers.SerializerMethodField("get_parent")

    def get_cover_image(self, category):
        if category.cover_image:
            return category.cover_image
        else:
            return ''

    def get_parent(self, category):
        if category.parent_id:
            return category.parent_id
        else:
            return -1

    class Meta:
        model = CourseCategory
        fields = ("id", "name", "cover_image", "parent_id")


class KnowledgeMapSerializer(serializers.ModelSerializer):

    def transform_introduction(self, obj, value):
        return _getTextFromHtml(value)

    class Meta:
        model = KnowledgeMap
        fields = ("id", "name", "introduction")


class KnowledgeMapTagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='tag')
    course_id = serializers.SerializerMethodField('get_course_id')

    def get_course_id(self, knowledgemaptag):
        return knowledgemaptag.course_id.course_id

    class Meta:
        model = CourseInKnowledgeMap
        fields = ("name", "level", "course_id", "priority")


class StaffSerializer(serializers.ModelSerializer):
    org = serializers.CharField(source='org_id')
    avatar = serializers.CharField(source='avartar')

    def transform_avatar(self, obj, value):
        return _normalizeUrl(value)

    class Meta:
        model = Staff
        fields = ("id", "name", "org", "company",
                  "department", "position", "avatar", "about")


class CourseSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='course_id')
    org_name = serializers.SerializerMethodField('get_org_name')
    enrollments = serializers.SerializerMethodField('get_enrollments')
    payment_type = serializers.SerializerMethodField('get_payment_type')
    enroll_status = serializers.SerializerMethodField('get_enroll_status')
    course_start_status = serializers.SerializerMethodField('get_course_start_status')
    chapter_num = serializers.SerializerMethodField('get_chapter_num')
    thumbnail = serializers.SerializerMethodField('get_thumbnail')
    thumbnail_1080x600 = serializers.SerializerMethodField('get_thumbnail_1080x600')
    staff = serializers.SerializerMethodField('get_staffs')

    def __init__(self, thumbnail_size, courses, **kwargs):
        self.thumbnail_size = thumbnail_size
        super(CourseSerializer, self).__init__(courses, **kwargs)

    def get_thumbnail(self, course):
        # return url according to thumbnail_size
        size_str = '{}x{}'.format(self.thumbnail_size[0], self.thumbnail_size[1])
        return course.gen_cover_url(course.course_id, course.thumbnail, course.cover_compressed, size_str)

    def get_thumbnail_1080x600(self, course):
        return self.transform_thumbnail(course, course.gen_cover_url(course.course_id, course.thumbnail,
                                                                     course.cover_compressed, '1080x600'))

    def get_chapter_num(self, course):
        try:
            m = CHAPTER_NUM_RE.match(course.length)
            if m:
                return int(m.group())
        except Exception:
            return 0
        return 0

    def get_staffs(self, course):
        staffs = []
        for cs in course.coursestaffrelationship_set.all():
            staff = StaffSerializer(cs.staff).data
            staff['role'] = cs.role
            staffs.append(staff)
        return staffs

    def transform_start(self, obj, value):
        return value.strftime(_datetime_format) if value else None

    def transform_end(self, obj, value):
        return value.strftime(_datetime_format) if value else None

    def transform_enrollment_start(self, obj, value):
        return value.strftime(_datetime_format) if value else None

    def transform_enrollment_end(self, obj, value):
        return value.strftime(_datetime_format) if value else None

    def transform_thumbnail(self, obj, value):
        # new storage
        if value.startswith(settings.COURSE_COMPRESSED_COVER_PATH):
            return value

        # Return directly if hit in cache
        cache_key = "api_thumbnail_cache." + value
        url = cache.get(cache_key)
        if url:
            return url
        log.info("Thumbnail cache not hit: %s" % value)

        m = re.match(
            '^https?://s.xuetangx.com/files/course/image/(.*)$', value)
        if m:
            url = "http://s.xuetangx.com/files/course/image/large/%s" % m.group(1)
            if _url_exists(url):
                cache.set(cache_key, url, 60 * 60 * 24)
                return url

        if value.startswith('http'):
            url = value
            if _url_exists(url):
                cache.set(cache_key, url, 60 * 60 * 24)
                return url

        try:
            url = "http://s.xuetangx.com/%s" % value.lstrip('/')
            if _url_exists(url):
                cache.set(cache_key, url, 60 * 60 * 24)
                return url
        except:
            pass

        DOMAIN = 'http://{}'.format(settings.LMS_BASE)
        url = "{}/{}".format(DOMAIN,  value.lstrip("/"))
        cache.set(cache_key, url, 60 * 60 * 24)
        return url

    def get_org_name(self, obj):
        cache_key = "api_org_name_cache.{}".format(obj.org)
        name = cache.get(cache_key)
        if name:
            return name
        if not obj.org:
            return ''
        orgs = Organization.objects.filter(org=obj.org).order_by('-id')
        if orgs.exists():
            org = orgs[0]
            name = org.name if org.name else org
            cache.set(cache_key, name, 60 * 60 * 12)
            return name
        else:
            log.error('找不到此org信息: {}'.format(obj.org))
            return ''

    def get_enrollments(self, obj):
        return course_stat.enrollment_total_count(
            SlashSeparatedCourseKey.from_deprecated_string(obj.course_id))

    def get_payment_type(self, obj):
        try:
            course_id = obj.course_id
            cache_key = "api_course_payment_cache.{}".format(course_id)
            payment_type = cache.get(cache_key, "")
            if payment_type:
                return payment_type.split("|")
            course_key = CourseKey.from_string(course_id)
            course_modes = CourseMode.modes_for_course(course_key)
            course_modes_dict = CourseMode.modes_for_course_dict(course_id, course_modes)
            has_verified_mode = CourseMode.has_verified_mode(course_modes_dict)
            SA = True
            ST = True if has_verified_mode else False
            if ST and not "honor" in course_modes_dict:
                SA = False
            if SA and ST:
                payment_type = "SA|ST"
            elif SA:
                payment_type = "SA"
            else:
                payment_type = "ST"
            cache.set(cache_key, payment_type, 60 * 60 * 6)
        except Exception as ex:
            # import traceback
            # traceback.print_exc()
            log.error(ex)
            payment_type = "SA"

        return payment_type.split("|")

    def get_enroll_status(self, obj):
        return obj.enroll_status

    def get_course_start_status(self, obj):
        return obj.start_status

    class Meta:
        model = Course
        fields = ("id", "org", "course_num", "name", "serialized", "owner",
                  "start", "end", "enrollment_start", "enrollment_end",
                  "thumbnail", "subtitle", "thumbnail_1080x600", "org_name", "enrollments", "payment_type",
                  "enroll_status", "course_start_status", "chapter_num", "staff")


class CourseWithoutStaffSerializer(CourseSerializer):
    def __init__(self, thumbnail_size, courses, **kwargs):
        self.thumbnail_size = thumbnail_size
        super(CourseWithoutStaffSerializer, self).__init__(self.thumbnail_size, courses, **kwargs)

    class Meta:
        model = Course
        fields = ("id", "org", "course_num", "name", "serialized", "owner",
                  "start", "end", "enrollment_start", "enrollment_end",
                  "thumbnail", "subtitle", "thumbnail_1080x600", "org_name", "enrollments", "payment_type",
                  "enroll_status", "course_start_status", "chapter_num")


class CourseWithCategorySerializer(CourseSerializer):
    categories = serializers.SerializerMethodField('get_categories')
    chapter_num = serializers.SerializerMethodField('get_chapter_num')

    def __init__(self, thumbnail_size, courses, **kwargs):
        self.thumbnail_size = thumbnail_size
        super(CourseWithCategorySerializer, self).__init__(self.thumbnail_size, courses, **kwargs)

    def get_categories(self, course):
        return CategorySerializer(course.category.all(), many=True).data

    def get_chapter_num(self, course):
        try:
            m = CHAPTER_NUM_RE.match(course.length)
            if m:
                return int(m.group())
        except Exception:
            return 0
        return 0

    class Meta:
        model = Course
        fields = ("id", "org", "course_num", "name", "serialized", "owner",
                  "start", "end", "enrollment_start", "enrollment_end",
                  "thumbnail", "thumbnail_1080x600", "org_name", "enrollments", "payment_type",
                  "enroll_status", "course_start_status", "categories",
                  "chapter_num")


class CourseDetailSerializer(CourseSerializer):
    intro_video_caption = serializers.SerializerMethodField('get_intro_video_caption')
    qas = serializers.SerializerMethodField('get_qas')
    chapters = serializers.SerializerMethodField('get_chapters')

    def __init__(self, thumbnail_size, courses, **kwargs):
        self.thumbnail_size = thumbnail_size
        super(CourseDetailSerializer, self).__init__(self.thumbnail_size, courses, **kwargs)

    def transform_video_thumbnail(self, obj, value):
        return _normalizeUrl(value) if value else ''

    def transform_chapters(self, obj, value):
        if value != []:
            result = []
            for chapter in re.findall('<dl>(.*?)</dl>', value):
                chapter_obj = {}
                m = re.search('<dt>(.*?)</dt>', chapter)
                if m:
                    chapter_obj["title"] = m.group(1)
                else:
                    chapter_obj["title"] = ''
                sq_array = []
                for sq in re.findall("<dd>(.*?)</dd>", chapter):
                    sq_array.append(_getTextFromHtml(sq))
                chapter_obj["sequentials"] = sq_array
                result.append(chapter_obj)
            return result
        else:
            return value

    def transform_about(self, obj, value):
        return _getTextFromHtml(value)

    def get_qas(self, obj):
        return QASerializer(obj.courseqa_set.all(), many=True).data if self.context['without_qas'] == 0 else []

    def get_chapters(self, obj):
        return obj.chapters if self.context['without_chapters'] == 0 else []

    def get_intro_video_caption(self, course):
        caption = "http://s.xuetangx.com/files/course/caption/%s.srt" % course.intro_video if course.intro_video else ''
        if not caption:
            return caption
        cache_key = "api_intro_video_caption_cache.{}".format(course.id)
        has_caption = cache.get(cache_key)
        if has_caption:
            return caption
        log.info("caption cache not hit: {}".format(caption))

        try:
            r = requests.head(caption)
            if r.status_code == status.HTTP_200_OK:
                cache.set(cache_key, caption, 60 * 60 * 24)
                return caption
        except:
            pass
        return ''

    class Meta:
        model = Course
        fields = ("id", "org", "course_num", "name", "serialized", "owner",
                  "start", "end", "enrollment_start", "enrollment_end", "thumbnail", "thumbnail_1080x600",
                  "subtitle", "intro_video", "video_thumbnail", "effort", "length",
                  "quiz", "prerequisites", "about", "chapters", "enrollments",
                  "payment_type", "enroll_status", "course_start_status",
                  "qas", "chapter_num", "intro_video_caption", "staff")


def _normalizeUrl(url):
    if url.startswith('//s.xuetangx.com/'):
        return 'http:{}'.format(url)

    if not url or re.match('^(https?:)?//', url):
        return url

    DOMAIN = 'http://{}'.format(settings.LMS_BASE)
    return "{}/{}".format(DOMAIN, url.lstrip("/"))


_block_tags = ("h3", "p", "ol", "ul", "li", "br\s*/?")
_block_pat = "</(%s)>" % "|".join(_block_tags)


def _url_exists(url):
    try:
        r = requests.head(url)
        if r.status_code == status.HTTP_200_OK:
            return True
    except:
        return False
    return False


def _getTextFromHtml(html):
    html = re.sub(_block_pat, "\n", html)
    html = re.sub("<[^>]*>", "", html)
    # Remove the mutiple new lines
    html = re.sub("^\s+", "", html)
    html = re.sub("\s+\n", "\n", html)
    return html

class QASerializer(serializers.ModelSerializer):

    class Meta:
        model = CourseQA
        fields = ("id", "question", "answer")


class UpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='id')
    date = serializers.CharField(source='date')
    content = serializers.CharField(source='content')
    course_id = serializers.CharField(source='course_id')

    def transform_date(self, obj, value):
        return value.strftime(_datetime_format) if value else None

    def transform_content(self, obj, value):
        return HTMLParser().unescape(_getTextFromHtml(value))

    class Meta:
        fields = ("id", "date", "content", "course_id")


class ChapterSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField('get_id')
    display_name = serializers.CharField(source='display_name')

    def get_id(self, obj):
        return _get_item_id(obj) if obj else ''

    def transform_display_name(self, obj, value):
        return value if value else ""

    class Meta:
        fields = ("id", "display_name")

class ChapterWithSequentialSerializer(ChapterSerializer):

    sequentials = serializers.SerializerMethodField('get_children')

    def get_children(self, chapter):
        return SequentialWithTypeSerializer(chapter.sequentials, many=True).data

    class Meta:
        fields = ("id", "display_name", "sequentials")

class SequentialSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField('get_id')
    display_name = serializers.CharField(source='display_name')

    def get_id(self, obj):
        return _get_item_id(obj) if obj else ''

    def transform_display_name(self, obj, value):
        return value if value else ""

    class Meta:
        fields = ("id", "display_name")


class SequentialWithTypeSerializer(SequentialSerializer):
    type = serializers.SerializerMethodField('get_type')

    def get_type(self, obj):
        try:
            return dict(obj.type)
        except Exception, e:
            log.warn(e)
            return {}

    class Meta:
        fields = ("id", "display_name", "type")

class VerticalsSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField('get_id')
    display_name = serializers.CharField(source='display_name')

    def get_id(self, obj):
        return _get_item_id(obj) if obj else ''


    def transform_display_name(self, obj, value):
        return value if value else ""

    class Meta:
        fields = ("id", "display_name")


class VerticalsWithChildrenSerializer(VerticalsSerializer):
    children = serializers.SerializerMethodField('get_children')

    def __init__(self, course_id, videoes, **kwargs):
        self.course_id = course_id
        super(VerticalsWithChildrenSerializer, self).__init__(videoes, **kwargs)

    def get_children(self, vertical):
        # TODO: Select the other serializers
        return VideoSerializer(self.course_id, vertical.children, many=True).data

    class Meta:
        fields = ("id", "display_name", "children")


class VideoSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField('get_id')
    display_name = serializers.CharField(source='display_name')
    source = serializers.SerializerMethodField('get_video_source')
    track_en = serializers.SerializerMethodField('get_track_en')
    track_zh = serializers.SerializerMethodField('get_track_zh')
    length = serializers.SerializerMethodField('get_length')

    def __init__(self, course_id, videoes, **kwargs):
        self.course_id = course_id
        self.course_key = SlashSeparatedCourseKey.from_string(self.course_id)
        super(VideoSerializer, self).__init__(videoes, **kwargs)

    def get_video_source(self, obj):
        source_url = obj.ccsource
        return source_url.strip()

    def get_id(self, obj):
        return _get_item_id(obj) if obj else ''

    def transform_display_name(self, obj, value):
        return value if value else ""

    def get_track_en(self, obj):
        _value = obj.transcripts.get('en_xuetangx', '')
        if _value:
            cleaned_value = AssetLocator.clean_keeping_underscores(_value)
            if self.course_key.deprecated:
                value = '/c4x/%s/%s/asset/%s' % (self.course_key.org, self.course_key.course, cleaned_value)
            else:
                value = '/asset-v1:%s+%s+%s+type@asset+block@%s' % (
                self.course_key.org, self.course_key.course, self.course_key.run, cleaned_value)
            return _normalizeUrl(value)
        else:
            return ''

    def get_track_zh(self, obj):
        _value = obj.transcripts.get('zh', '')
        if _value:
            cleaned_value = AssetLocator.clean_keeping_underscores(_value)
            if self.course_key.deprecated:
                value = '/c4x/%s/%s/asset/%s' % (self.course_key.org, self.course_key.course, cleaned_value)
            else:
                value = '/asset-v1:%s+%s+%s+type@asset+block@%s' % (
                self.course_key.org, self.course_key.course, self.course_key.run, cleaned_value)
            return _normalizeUrl(value)
        else:
            return ''

    def get_length(self, video):
        try:
            ccsource = video.ccsource.strip()
            length = VideoInfo.objects.get(vid=ccsource).duration
            if length <= 0:
                return _get_video_info(ccsource).duration
            return length
        except:
            return _get_video_info(video.ccsource).duration

    class Meta:
        fields = (
            "id", "display_name", "source", "track_en", "track_zh", "length")


def _get_video_info(vid):
    info = get_video_info(vid)
    try:
        v_temp = VideoInfo.objects.get(vid=vid)
    except:
        v_temp = None

    if v_temp:
        videoInfo = v_temp
    else:
        videoInfo = VideoInfo(vid=vid)

    if info:
        videoInfo.status = 'OK'
        videoInfo.duration = info.get('duration')
        videoInfo.image = info.get('image')
    else:
        videoInfo.status = 'NotExist'
        videoInfo.duration = -1
        videoInfo.image = ''
    videoInfo.save()
    return videoInfo


def _get_item_id(value):
    _id = ''
    try:
        _id = value.location.block_id
    except Exception as ex:
        log.warn(ex)
    return _id


class BannerSerializer(serializers.ModelSerializer):
    message = serializers.SerializerMethodField('get_message')

    def get_message(self, obj):
        # TODO: 移动端以后会要
        return ''

    class Meta:
        model = Banner
        fields = ('name', 'introduction', 'image', 'image_big', 'type', 'location', 'message')


class SplashScreenSerializer(serializers.ModelSerializer):

    class Meta:
        model = SplashScreen
        fields = ('period', 'start', 'end', 'url', 'message')


class VersionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppVersion
        fields = ('version', 'url', 'size', 'description', 'release_date')


class CaptionSerializer(serializers.Serializer):
    course_id = serializers.CharField(source='course_id')
    sequential_id = serializers.SerializerMethodField('get_sequential_id')
    vertical_id = serializers.SerializerMethodField('get_vertical_id')
    video_id = serializers.SerializerMethodField('get_video_id')
    source = serializers.CharField(source='source')
    timestamp = serializers.CharField(source='timestamp')
    description = serializers.CharField('description')

    def get_sequential_id(self, caption):
        try:
            return caption['id']['names']['sequential']
        except:
            return ''

    def get_vertical_id(self, caption):
        try:
            return caption['id']['names']['vertical']
        except:
            return ''

    def get_video_id(self, caption):
        try:
            return caption['id']['names']['video']
        except:
            return ''

    class Meta:
        fields = (
            "course_id", "sequential_id", "vertical_id", "video_id", "source", "timestamp", "description")


# TODO: This serializer is unfinished
class CommentSerializer(serializers.ModelSerializer):
    meta = serializers.SerializerMethodField('get_meta')

    def transform_create_time(self, obj, value):
        return value.strftime(_datetime_format) if value else None

    def transform_update_time(self, obj, value):
        return value.strftime(_datetime_format) if value else None

    def get_meta(self, comment):
        return comment.get_meta()

    class Meta:
        model = Comment
        fields = ('id', 'title', 'content', 'create_time',
                  'update_time', 'user_id', 'status', 'type', 'meta', 'location')


class LogUploadStrategySerializer(serializers.ModelSerializer):

    onLaunch = serializers.CharField(source='on_launch')
    openWifi = serializers.CharField(source='open_wifi')
    skipPages = serializers.CharField(source='skip_pages')

    class Meta:
        model = LogUploadStrategy
        fields = ('onLaunch', 'openWifi', 'size', 'interval', 'skipPages', 'device')


class WisdomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wisdom
        fields = ('id', 'content')


class FragmentKnowledgeSerializer(serializers.ModelSerializer):
    web_address = serializers.SerializerMethodField('get_web_address')
    location = serializers.SerializerMethodField(
        'get_location')  # Model property override fields， 需要单独在这里写， 3.0以上就不需要了，可以直接加到fields里面

    def get_web_address(self, fragment):
        _url = reverse('hybrid_fragment_detail', kwargs={'fragment_id': fragment.id})
        DOMAIN = 'http://{}'.format(settings.LMS_BASE)
        _url_with_domain = "{}/{}".format(DOMAIN.rstrip('/'), _url.lstrip("/"))
        return _url_with_domain

    def get_location(self, fragment):
        return fragment.course_id.make_usage_key('video', fragment.block_id).to_deprecated_string()

    class Meta:
        model = FragmentKnowledge
        fields = ("id", "title", "description", "cover_image", "provider", "course_id",
                  "block_id", "location", "chapter_num", "sequential_num",
                  "difficulty", "value",
                  # "share_text",
                  "view_number",
                  # "related_to_fragment", "tags",
                  # "topic", "create_time", "updated_time",
                  'web_address'
                  )
