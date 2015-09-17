define(['underscore', 'Framework7', 'src/util'], function (_) {
	var $$ = Framework7.$;
	var xt_router = {
		moren: function(myApp, content, url, next){
			next(_.template(content)());
		},
		edituserinfo: function(myApp, content, url, next){
			var template = _.template(content),
				resultContent = '';
		    // For example, we will retreive template JSON data using Ajax and only after that we will continue page loading process
		    var storedData = myApp.formGetData('form_userinfo');
		    if(storedData) {
		    	storedData.userinfoHasBack = direction.userinfoHasBack;
		    	resultContent = template(storedData);
		    	next(resultContent);
		    }
		    else {
		    	$$.get(xt_api.teacher.userinfo, function(data) {
		    		data = JSON.parse(data);
		    	    
		    	    data.userinfoHasBack = direction.userinfoHasBack;
		    	    resultContent = template(data);
		    	
		    	    next(resultContent);
		    	});
		    }
		},
		course: function(myApp, content, url, next){
			$$.get(xt_api.teacher.course, function(data) {
				data = JSON.parse(data);
				
			    next(_.template(content)(data));
			});
		}
	};
	return xt_router;
});
	
