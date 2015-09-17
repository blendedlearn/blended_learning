//email validation
function isEmail(str){
	var reg = /^([a-zA-Z0-9_-])+@([a-zA-Z0-9_-])+(.[a-zA-Z0-9_-])+/;
	return reg.test(str);
}

var direction = {
	userinfoHasBack: false
};

var xt_api = {
	//学生端
	'student': {},
	//教师端
	'teacher': {
		//填写个人信息页面需要
		'userinfo': '../../static/js/src/data/teacher/userinfo.json',
		'edituserinfo': '../../static/js/src/data/teacher/edituserinfo.json',
		'course': '../../static/js/src/data/teacher/course.json'
	}
};