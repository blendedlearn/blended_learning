# -*- coding: utf-8 -*-
from django.contrib import admin
from api.models import LogUploadStrategy, Banner, SplashScreen, Wisdom, AppVersion


class LogUploadStrategyAdmin(admin.ModelAdmin):
    list_filter = ('enabled', 'device')
    list_display = ('id', 'on_launch', 'open_wifi', 'size', 'interval', 'skip_pages', 'device', 'enabled')
    ordering = ('-updated_at',)


class BannerAdmin(admin.ModelAdmin):
    list_filter = ('is_active', 'type', 'belong', 'channel')
    list_display = ('id', 'name', 'type', 'order', 'location', 'is_active', 'belong', 'channel')
    ordering = ('order',)


class SplashScreenAdmin(admin.ModelAdmin):
    list_filter = ('screen_id', 'is_active')
    list_display = ('screen_id', 'period', 'width', 'height', 'start', 'end', 'url', 'is_active')
    ordering = ('screen_id', 'start')


class WisdomAdmin(admin.ModelAdmin):
    list_filter = ('enabled',)
    list_display = ('id', 'content', 'enabled', 'created', 'updated')
    ordering = ('-id',)


class AppVersionAdmin(admin.ModelAdmin):
    list_filter = ('platform',)
    list_display = ('platform', 'channel', 'version', 'url', 'size', 'description', 'release_date')
    ordering = ('-id',)

admin.site.register(LogUploadStrategy, LogUploadStrategyAdmin)
admin.site.register(Banner, BannerAdmin)
admin.site.register(SplashScreen, SplashScreenAdmin)
admin.site.register(Wisdom, WisdomAdmin)
admin.site.register(AppVersion, AppVersionAdmin)
