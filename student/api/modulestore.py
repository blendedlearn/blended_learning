from xmodule.modulestore import Location
from xmodule.modulestore.django import modulestore
from datetime import datetime
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locations import SlashSeparatedCourseKey
import calendar
import re
import logging

log = logging.getLogger(__name__)

def get_course_updates(course_id, timestamp=None):
    from course_meta.parser import get_updates
    if isinstance(course_id, basestring):
        course_id = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    try:
        data = get_updates(course_id).data
    except Exception as ex:
        log.warn(ex)
        return []

    result = []
    updates = re.findall('<article><h2>(.*?)</h2>(.*?)</article>', data, re.DOTALL)
    total = len(updates)

    if total == 0:
        updates = re.findall('<li><h2>(.*?)</h2>(.*?)</li>', data, re.DOTALL)
    total = len(updates)

    for idx, (date, content) in enumerate(updates):
        try:
            date = datetime.strptime(date, "%B %d, %Y")
            result.append({
                "id": total - idx,
                "date": date,
                "content": content,
                "course_id": str(course_id),
            })
            if timestamp:
                ts = calendar.timegm(date.utctimetuple())
                if ts <= timestamp:
                    return result
        except:
            pass
    return result


def get_items(course_id, category):
    #org, course_num, run = course_id.split("/")
    #loc = Location('i4x', org, course_num, category)
    try:
        if not isinstance(course_id, CourseKey):
            course_id = SlashSeparatedCourseKey.from_string(course_id)
        data = modulestore().get_items(course_id, qualifiers={'category':category})
    except:
        return []

    return data


def get_item(course_id, category, id):
    try:
        if isinstance(course_id, basestring):
            course_id = SlashSeparatedCourseKey.from_string(course_id)
        usage_key = course_id.make_usage_key(category, id)
        data = modulestore().get_item(usage_key)
    except Exception as ex:
        log.warn(ex)
        return None

    return data


def get_course(course_id):
    try:
        if not isinstance(course_id, CourseKey):
            course_id = SlashSeparatedCourseKey.from_string(course_id)
        return modulestore().get_course(course_id)
    except:
        return None
