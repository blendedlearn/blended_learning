# coding=utf-8
import json
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from course_meta.models import CourseCategory, CategoryGroup, KnowledgeMap, Course
# from student.tests.factories import UserFactory
# from xmodule.modulestore.tests.factories import CourseFactory
# from xmodule.modulestore.tests.django_utils import (
#     ModuleStoreTestCase, mixed_store_config
# )
class CourseTest(APITestCase):

    # USERNAME = "Bob"
    # EMAIL = "bob@example.com"
    # PASSWORD = "edx"
    def setUp(self):
        # super(CourseTest, self).setUp()
        #
        # self.course = CourseFactory.create()
        # self.user = UserFactory.create(username=self.USERNAME, email=self.EMAIL, password=self.PASSWORD)
        # self.client.login(username=self.USERNAME, password=self.PASSWORD)

        self.user_info_with_email = {'username': 'lushiyong', 'password': '123456', 'email': 'lushiyong@xuetangx.com'}
        self.c_group = CategoryGroup()
        self.c_group.slug = '/'
        self.c_group.name = 'test_group'
        self.c_group.active = 1
        self.c_group.desp = 'desp'
        self.c_group.owner = 'owner'
        self.c_group.save()

        self.course_cate = CourseCategory()
        self.course_cate.parent_id = 1
        self.course_cate.name = 'test'
        self.course_cate.group = self.c_group
        self.course_cate.save()

        self.course = Course()
        self.course.course_id = 'xuetangX/testcs1/2014_T1'
        self.course.status = 1
        self.course.serialized = 1
        self.course.save()
        self.course.category.add(self.course_cate)
        self.course.save()

        self.km = KnowledgeMap()
        self.km.name = 'km_name'
        self.km.save()

    def test_v2_get_categories(self):
        test_url = reverse('api:v2_categories')
        # print test_url
        response = self.client.get(test_url)
        # print response
        content = json.loads(response.content)
        # print content
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_category_courses(self):  # TODO  mock Course serilizer ?
        test_url = reverse('api:v2_get_category_courses', kwargs={'cid': self.course_cate.id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        content = json.loads(response.content)
        # print content
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_knowledgemaps(self):
        test_url = reverse('api:v2_get_knowledgemaps')
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_knowledgemap_tags(self):
        test_url = reverse('api:v2_get_knowledgemap_tags', kwargs={'kid':1})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_knowledgemap_couses(self):
        test_url = reverse('api:v2_get_knowledgemap_couses', kwargs={'kid':1})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_courses(self):
        test_url = reverse('api:v2_get_courses')
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_courses_hot(self):
        test_url = reverse('api:v2_courses_hot')
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_courses_recent(self):
        test_url = reverse('api:v2_courses_recent')
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_courses_enroll(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')
        test_url = reverse('api:v2_courses_enroll')
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_course_updates(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')
        test_url = reverse('api:v2_courses_updates')
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_course_follow(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        test_url = reverse('api:v2_courses_follow')
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_details(self):  # TODO  mock Course serilizer ?
        test_url = reverse('api:v2_get_course_details', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_categories(self):
        test_url = reverse('api:v2_get_course_categories', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_staffs(self):
        test_url = reverse('api:v2_get_course_staffs', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_qas(self):
        test_url = reverse('api:v2_get_course_qas', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_enroll_course(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        # get request   TODO get error
        test_url = reverse('api:v2_enroll_course', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

        # TODO post request
        pass
        # TODO delete request
        pass

    def test_v2_fellow_course(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        # get request
        test_url = reverse('api:v2_fellow_course', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # TODO post request
        pass
        # TODO delete request
        pass

    def test_v2_get_course_updates(self):
        # get request
        test_url = reverse('api:v2_get_course_updates', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_enrollments(self):
        # get request
        test_url = reverse('api:v2_get_course_enrollments', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_comments(self):
        # get request
        test_url = reverse('api:v2_get_course_comments', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_freqdata(self):
        # get request
        test_url = reverse('api:v2_get_course_freqdata', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_chapters(self):  # TODO
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')
        # get request
        test_url = reverse('api:v2_get_course_chapters', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_course_chapter_sequentials(self): # TODO
        pass

    def test_v2_get_course_sequential_verticals(self): # TODO
        pass

    def test_v2_course_sync(self):  # TODO
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        # get request
        test_url = reverse('api:v2_course_sync', kwargs={'course_id': self.course.course_id})
        # print test_url
        response = self.client.get(test_url)
        # print response
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # TODO post request
        pass
        # TODO delete request
        pass

    def test_v2_get_courses_status(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        # get request
        test_url = reverse('api:v2_get_courses_status')
        # print test_url
        response = self.client.get(test_url)
        print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_honors(self):
        test_url = reverse('api:v2_user_register')
        # print test_url
        self.client.post(test_url, self.user_info_with_email)
        self.client.login(username='lushiyong', password='123456')

        test_url = reverse('api:v2_get_honors')
        # pritn test_url
        response = self.client.get(test_url)
        # print response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v2_get_video_quality(self):
        # TODO
        pass
    def test_v2_search(self):
        # TODO
        pass
    def test_v2_search_hot(self):
        # TODO
        pass
