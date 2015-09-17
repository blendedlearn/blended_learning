define(['src/teacher_router', 'Framework7', 'src/util'], function (xt_router) {
	var myApp = new Framework7({
		//不希望被缓存的url，数据json的地址
		// cacheIgnore: [],
		//进入不同的页面之前预处理数据
	    preprocess: function (content, url, next) {
	    	switch(url){
	    		case 'edituserinfo.html':
	    			xt_router.edituserinfo(myApp, content, url, next);
	    			break;
    			case 'course.html':
	    			xt_router.course(myApp, content, url, next);
	    			break;
    			default:
    				xt_router.moren(myApp, content, url, next);
	    	}
	    },
		onAjaxStart: function (xhr) {
	        myApp.showIndicator();
	    },
	    onAjaxComplete: function (xhr) {
	        myApp.hideIndicator();
	    }
	});

	var $$ = Framework7.$;

	var mainView = myApp.addView('.view-main', {
	  	dynamicNavbar: true
	});

	// mainView.router.loadPage('edituserinfo.html');
	mainView.router.loadPage('course.html');

	$$(document).on('click', function (e) {
		var id = e.target.id;
		if(id == 'userinfo_confirm'){
			var userinfo = myApp.formToJSON('#form_userinfo');
			userinfo.name = userinfo.name.replace(/ /g, '');
			
			if(!userinfo.name){
				myApp.alert('请输入姓名', ['']);
				return;
			}
			if(!isEmail(userinfo.email)){
				myApp.alert('请输入合法的邮箱', ['']);
				return;
			}

			$$.post(xt_api.teacher.edituserinfo, userinfo, function (data) {
				data = JSON.parse(data);
				if(data.success){
					myApp.formStoreData('form_userinfo', userinfo);
					//TODO 弹窗修改完成
					mainView.router.loadPage('course.html');
				}
			  
			});
		}

		if(id == 'userinfo_to_edituserinfo'){
			direction.userinfoHasBack = true;
			mainView.router.loadPage('edituserinfo.html');
		}
	});
});
	
