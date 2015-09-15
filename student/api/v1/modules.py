from ..models import VideoInfo
from django.conf import settings
from pymongo import Connection


def dbConnection():
    db = Connection(settings.MONGO_HOST, int(settings.MONGO_PORT))
    collection = db['edxapp'].modulestore
    return collection


def get_course_indb():
    con = dbConnection()
    courses = con.find({"_id.course": {'$ne': 'templates'},
                       "_id.category": "about", "_id.name": "overview"})
    course_list = []
    for course in courses:
        course_message = {}
        course_message['short_description'] = course['definition']['data']
        cid = course['_id']
        tmp = get_course_message(cid['course'], cid['org'], con, 'course')
        c_d = tmp['metadata']
        course_message['course_id'] = tmp['_id']['org'] + \
            '.' + tmp['_id']['course'] + '.' + tmp['_id']['name']
        course_message['display_name'] = c_d['display_name']
        course_message['start'] = c_d['start']
        course_message['display_org'] = cid['org']
        course_message['display_coursenum'] = 'null'
        course_message['advertised_start'] = 'null'
        course_message['course_image_url'] = "/c4x/" + cid['org'] + \
            '/' + cid['course'] + "/asset/images_course_image.jpg"
        c_d = con.find_one({"_id.course": cid['course'], "_id.org": cid[
                           'org'], '_id.category': 'about', '_id.name': 'effort'})
        if c_d != None:
            course_message['effort'] = c_d['definition']['data']
        else:
            course_message['effort'] = 'null'
        c_d = con.find_one({"_id.course": cid['course'], "_id.org": cid[
                           'org'], '_id.category': 'about', '_id.name': 'video'})
        if c_d != None:
            video_tmp = c_d['definition']['data']
            start = video_tmp.find('&&')
            end = video_tmp.find('\" frame')
            if start >= 0 and end > start:
                course_message['marketing_video_url'] = video_tmp[
                    start + 2:end]
            else:
                course_message['marketing_video_url'] = 'null'
        else:
            course_message['marketing_video_url'] = 'null'
        course_list.append(course_message)
    data = {"status": "success", "courses": course_list}
    return data


def get_course_message(course_id, course_org, con, category):
    items = con.find_one({"_id.course": course_id, "_id.org":
                         course_org, "_id.category": category, "_id.revision": None})
    return items


def get_all_course(course):
    data = {}
    courses = []
    con = dbConnection()
    for item in course:
        c = item.split('/')
        c_d = get_course_message(c[1], c[0], con, 'course')['metadata']
        course_data = {'display_name': c_d['display_name'], 'start': c_d[
            'start'], 'course_id': item.replace('/', '.'), 'display_org': c[0]}
        course_data['display_coursenum'] = 'None'
        '''course_data['advertised_start'] = 'None'
    course_data['short_description'] = 'None'
    course_data['marketing_video_url'] = 'None'''
        course_data['course_image_url'] = "/c4x/" + c[0] + \
            "/" + c[1] + "/asset/images_course_image.jpg"
        courses.append(course_data)
    data['enrollments'] = courses
    return data


def get_one_course(course_id, course_org, course_name):
    con = dbConnection()
    course = get_course_message(course_id, course_org, con, 'course')
    c = course['metadata']
    data = {'status': 'success'}
    course_data = {'location': 'i4x://' + course_org + '/' + course_id +
                   '/' + course_name, 'display_name': c['display_name'], 'start': c['start']}
    course_children = course['definition']['children']
    course_data_children = []


    # get chapters
    for item in course_children:
        loc = item.split('/')
        chapter_loc = loc[-1]
        chapter = get_item_message(
            con, course_id, course_org, 'chapter', chapter_loc)
        chapter_data = analyzer(chapter, item)
        chapter_children = get_children(chapter)
        chapter_data_children = []

        # get sequentials
        for sq_item in chapter_children:
            sq_loc = sq_item.split('/')
            sq_name = sq_loc[-1]
            seq = get_item_message(
                con, course_id, course_org, 'sequential', sq_name)
            seq_data = analyzer(seq, sq_item)
            seq_children = get_children(seq)
            seq_data_children = []
            for vir_item in seq_children:
                vir_loc = vir_item.split('/')
                vir_name = vir_loc[len(vir_loc) - 1]
                virtical = get_item_message(
                    con, course_id, course_org, 'vertical', vir_name)
                virtical_data = analyzer(virtical, vir_item)
                virtical_children = get_children(virtical)
                vir_data_children = []
                for union_item in virtical_children:
                    union_loc = union_item.split('/')
                    union_name = union_loc[len(union_loc) - 1]
                    union = get_item_message(
                        con, course_id, course_org, 'video', union_name)
                    union_data = video_analyzer(union, union_item)
                    vir_data_children.append(union_data)
                virtical_data['children'] = vir_data_children
                seq_data_children.append(virtical_data)
            seq_data['children'] = seq_data_children
            chapter_data_children.append(seq_data)
        chapter_data['children'] = chapter_data_children
        course_data_children.append(chapter_data)
    course_data['children'] = course_data_children
    data['course'] = course_data
    return data


def get_item_message(con, course_id, course_org, category, name):
    item = con.find_one({"_id.course": course_id, "_id.org": course_org,
                        "_id.category": category, "_id.revision": None, "_id.name": name})
    return item


def analyzer(item, loc):
    if item == None:
        return {}
    c = item['metadata']
    name = c.get('display_name')
    if not name:
        name = ''
    msg = {'location': loc, 'display_name': name}
    start = c.get('start')
    if not start:
        start = 'null'
    msg['start'] = start
    return msg


def video_analyzer(item, loc):
    if item == None:
        return {}
    c = item['metadata']
    name = c.get('display_name')
    if name == None:
        name = ''
    msg = {'location': loc, 'display_name': name}
    start = c.get('start')
    if start == None:
        start = 'null'
    track_zh = c.get('track_zh')
    if track_zh == None:
        track_zh = 'null'
    track_en = c.get('track_en')
    if track_en == None:
        track_en = 'null'
    msg['start'] = start
    msg['track_en'] = track_en
    msg['track_zh'] = track_zh
    msg['source'] = c.get('source')
    return msg


def get_children(item):
    if item == None:
        return []
    if item['definition'].get('children') == None:
        return []
    return item['definition']['children']
