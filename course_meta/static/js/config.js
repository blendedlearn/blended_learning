
var require = {
	baseUrl: '../static/js',
	paths: {
		//模块路径定义
		'text': 'libs/text',
		'jquery': 'libs/jquery',
		'zepto': 'libs/zepto',
		'backbone':"libs/backbone",
		'underscore':"libs/underscore",
		'bootstrap': 'plugins/bootstrap',
		'cookie': 'plugins/jquery.cookie',
		'datepicker': 'plugins/bootstrap-datepicker',
		'datepicker_locale': 'plugins/bootstrap-datepicker.zh-CN',
		'umeditor': 'plugins/umeditor/umeditor.min',
		'umeditor_config': 'plugins/umeditor/umeditor.config',
		'umeditor_locale': 'plugins/umeditor/umeditor.zh-cn',
		'fileupload': 'plugins/jquery.fileupload',
		'jquery.ui.widget': 'plugins/jquery.ui.widget',
		'iframe_transport': 'plugins/jquery.iframe-transport',
		'simplePagination': 'libs/jquery.simplePagination',
		'swiper': 'libs/hack_swiper.min',
		'weixin': 'libs/jweixin-1.0.0',
		'Framework7': 'libs/framework7'
	},
	shim: {
		backbone: {
			deps: ['jquery', 'underscore'],
			exports: 'Backbone'
		},
		bootstrap: {
			deps: ['jquery']
		},
		datepicker_locale: {
			deps: ['datepicker']
		},
		umeditor: {
			deps: ['umeditor_config']
		},
		umeditor_locale: {
			deps: ['umeditor']
		}
	}
};