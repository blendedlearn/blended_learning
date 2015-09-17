define(['text!src/tpl/video.html', 'text!src/tpl/image.html', 'text!src/tpl/problem.html', 'underscore', 'weixin', 'zepto', 'swiper'], function (videoTpl, imageTpl, problemTpl, _, wx) {
	$(function(){
		/*var swiper = new Swiper('.swiper-container', {
		    spaceBetween: 50,
		    slidesPerView: 1,
		    // centeredSlides: true,
		    // slideToClickedSlide: true,
		    // grabCursor: true,
		    // spaceBetween: 0,
		    // slidesOffsetBefore: 0,
		    // slidesOffsetAfter: 0,
		    // height: 568,
		    // height: '100%',
		    // nextButton: '.swiper-button-next',
		    // prevButton: '.swiper-button-prev',
		    // scrollbar: '.swiper-scrollbar',
		    // pagination: '.swiper-pagination',
		    direction: 'vertical',
		    onSlideChangeEnd: function(s){
		    	
		    	var idx = s.activeIndex;
		    	$('video').each(function(){
		    		this.pause();
		    	});
		    	
		    }
		});*/

		/*$.getJSON('https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx33773d39d757855c&secret=e6981ac9ec5ad613229eae70a1269478&jsoncallback=?',
	      function(json){
	      console.log(json);
	    });*/

		/*$.ajax({
            url:'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx33773d39d757855c&secret=e6981ac9ec5ad613229eae70a1269478',
            dataType:"jsonp",
            jsonp:"jsonpcallback",
            success:function(data){
                console.log(data);
            }
        });*/


		/*
		 * 注意：
		 * 1. 所有的JS接口只能在公众号绑定的域名下调用，公众号开发者需要先登录微信公众平台进入“公众号设置”的“功能设置”里填写“JS接口安全域名”。
		 * 2. 如果发现在 Android 不能分享自定义内容，请到官网下载最新的包覆盖安装，Android 自定义分享接口需升级至 6.0.2.58 版本及以上。
		 * 3. 常见问题及完整 JS-SDK 文档地址：http://mp.weixin.qq.com/wiki/7/aaa137b55fb2e0456bf8dd9148dd613f.html
		 *
		 * 开发中遇到问题详见文档“附录5-常见错误及解决办法”解决，如仍未能解决可通过以下渠道反馈：
		 * 邮箱地址：weixin-open@qq.com
		 * 邮件主题：【微信JS-SDK反馈】具体问题
		 * 邮件内容说明：用简明的语言描述问题所在，并交代清楚遇到该问题的场景，可附上截屏图片，微信团队会尽快处理你的反馈。
		 */
		wx.config({
		    debug: true,
		    appId: 'wxf8b4f85f3a794e77',
		    timestamp: 1441613897,
		    nonceStr: 'GhhuMaNeJxX71OQH',
		    signature: 'ade88c4aa1fcc7daf08694d141aa145196ef5e2e',
		    jsApiList: [
		      'checkJsApi',
		      'onMenuShareTimeline',
		      'onMenuShareAppMessage',
		      'onMenuShareQQ',
		      'onMenuShareWeibo',
		      'onMenuShareQZone',
		      'hideMenuItems',
		      'showMenuItems',
		      'hideAllNonBaseMenuItem',
		      'showAllNonBaseMenuItem',
		      'translateVoice',
		      'startRecord',
		      'stopRecord',
		      'onVoiceRecordEnd',
		      'playVoice',
		      'onVoicePlayEnd',
		      'pauseVoice',
		      'stopVoice',
		      'uploadVoice',
		      'downloadVoice',
		      'chooseImage',
		      'previewImage',
		      'uploadImage',
		      'downloadImage',
		      'getNetworkType',
		      'openLocation',
		      'getLocation',
		      'hideOptionMenu',
		      'showOptionMenu',
		      'closeWindow',
		      'scanQRCode',
		      'chooseWXPay',
		      'openProductSpecificView',
		      'addCard',
		      'chooseCard',
		      'openCard'
		    ]
		});

		var voice = {};

		$('#closeFloater').tap(function(){
			$('video').each(function(){
				this.pause();
			});
			$('#floater').hide();
			$('#closeFloater').hide();
		});

		$('video').on('play', function(){
			$('#floater').show().css('opacity', 0);
			$('#closeFloater').show();
		});

		$('video').on('pause', function(){
			$('#floater').hide();
			$('#closeFloater').hide();
		});


		wx.ready(function(){
			$('#luyin').on('tap', function(){
				wx.startRecord({
			      cancel: function () {
			        alert('用户拒绝授权录音');
			      }
			    });
			});
			$('#stopluyin').on('tap', function(){
				wx.stopRecord({
			      success: function (res) {
			        voice.localId = res.localId;
			      },
			      fail: function (res) {
			        alert(JSON.stringify(res));
			      }
			    });
			});

			$('#playluyin').on('tap', function(){
				wx.playVoice({
			      localId: voice.localId
			    });
			});
		});

		function renderSwiper(){
			var swiper = new Swiper('.swiper-container', {
			    spaceBetween: 50,
			    slidesPerView: 1,
			    pagination: '.swiper-pagination',
			    direction: 'vertical',
			    scrollbar: '.swiper-scrollbar',
			    paginationClickable: true,
                paginationBulletRender: function (index, className) {
                	return '<span class="swiper-pagination-bullet">' + (index + 1) + '</span>';
             	},
			    onSlideChangeEnd: function(s){
			    	var idx = s.activeIndex;
			    	$('video').each(function(){
			    		this.pause();
			    	});
			    }
			});
		}

		$.ajax({
			type: "get",
			url: '../static/js/src/data/bl_done.json',
			dataType: "json",
			success: function(data, status){
				var list = data.cards;

				for (var i = 0; i < list.length; i++) {
					var type = list[i].type;
					if(type == 'video'){
						var compiled = _.template(videoTpl)(list[i]);
						$('.swiper-wrapper').append(compiled);
					}else if(type == 'image'){
						var compiled = _.template(imageTpl)(list[i]);
						$('.swiper-wrapper').append(compiled);
					}else if(type == 'problem'){
						var compiled = _.template(problemTpl)(list[i]);
						$('.swiper-wrapper').append(compiled);
					}
					
				};

				renderSwiper();
				var WIDTH = $(window).width(),
					HEIGHT = $(window).height();

			},
			error: function(xhr, errorType, error){
				console.log(error);
			}
		});
	});
});