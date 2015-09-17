# -*- coding: utf-8 -*-
from django.conf.urls import patterns, include, url
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'blended_learning.views.home', name='home'),
    # url(r'^blended_learning/', include('blended_learning.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    # url(r'', include('blended_learning.urls')),
    # url(r'', include('student.urls')),
    # url(r'', include('cards.url')),
    # url(r'', include('course_meta.urls')),
    url(r'^$', 'student.views.index'),
    url(r'', include('social_auth.urls')),
    url(r'^$','student.views.index'),
    url(r'^create_classroom$', 'student.views.create_classroom', name='create_classroom'),
    url(r'^delete_classroom$', 'student.views.delete_classroom', name='delete_classroom'),
    url(r'^logout_user$', 'student.views.logout_user', name='logout_user'),
    # oauth default urls
    url(r'^complete/(?P<backend>[^/]+)/$', 'social_auth.views.complete', name='socialauth_complete'),
    url(r'^associate/(?P<backend>[^/]+)/$', 'social_auth.views.auth', name='socialauth_associate_begin'),
    url(r'^associate/complete/(?P<backend>[^/]+)/$', 'social_auth.views.complete', name='socialauth_associate_complete'),
    url(r'^disconnect/(?P<backend>[^/]+)/$', 'social_auth.views.disconnect', name='socialauth_disconnect'),
    url(r'^disconnect/(?P<backend>[^/]+)/(?P<association_id>[^/]+)/$', 'social_auth.views.disconnect', name='socialauth_disconnect_individual'),

    # our oauth urls
    url(r'^login/(?P<backend>[^/]+)/$', 'social_oauth.views.oauth_login', name='oauth_login'),
    url(r'^register/(?P<backend>[^/]+)/$', 'social_oauth.views.oauth_register', name='oauth_register'),
    url(r'^bind/(?P<backend>[^/]+)/$', 'social_oauth.views.oauth_bind', name='oauth_bind'),
    url(r'^oauth/newassociation$', 'social_oauth.views.new_association', name='new_association'),
    url(r'^oauth/authentication/success$', 'social_oauth.views.authentication_success', name='authentication_success'),
)
if settings.DEBUG:
    urlpatterns += patterns('django.contrib.staticfiles.views',
        url(r'^static/(?P<path>.*)$','server'),
        )
