var OPERATION_SUCCESS = 1,
    OPERATION_FAIL = 2,
    INIT = '11',
    RUNNING = '12',
    SUSPEND = '13',
    ERROR = '14';

$.ajaxSetup({
        type : "POST", url : "/course_meta/j", cache : false, dataType : "json"
});

function change_course_name(obj){
    var name = $(obj).attr("name"),
        target_text = $(obj).text(),
        course_id = $("#change_course_name").data("course-id"),
        course_name = "";
    $(obj).html("<input style='width:200px;' type='text' name='"+name+"' value='"+target_text+"'>");
    $(obj).removeAttr('onclick');
    $(obj).removeAttr('name');
    $("input[name='"+name+"']").focus().on('blur',function(){
     var value = $(this).val();
     $(this).parent().attr("name",name);
     $(this).parent().attr("onclick","change_course_name(this);");
     $(this).parent().html(value);
     course_name = $("#change_course_name").text();
    $.ajax({
        data : {
            "type":"change_course_name",
            "course_id":course_id,
            "course_name":course_name
        },
        success : function (result) {
            if (result.status === OPERATION_SUCCESS) {
                console.log("success");
            } else {
                alert("修改course_name 失败");
            }
        }
    });
    });
    $("input[name='"+name+"']").keyup(function(event){
         if(event.keyCode == 13){
             $(this).blur();
         }
    });
} 

function change_classroom_name(obj){
    var name = $(obj).attr("name"),
        target_text = $(obj).text(),
        classroom_id = $("#change_classroom_name").data("classroom-id"),
        classroom_name = "";
    $(obj).html("<input style='width:200px;' type='text' name='"+name+"' value='"+target_text+"'>");
    $(obj).removeAttr('onclick');
    $(obj).removeAttr('name');
    $("input[name='"+name+"']").focus().on('blur',function(){
     var value = $(this).val();
     $(this).parent().attr("name",name);
     $(this).parent().attr("onclick","change_course_name(this);");
     $(this).parent().html(value);
     classroom_name = $("#change_classroom_name").text();
     console.log(classroom_id);
     console.log(classroom_name);
    $.ajax({
        data : {
            "type":"change_classroom_name",
            "classroom_id":classroom_id,
            "classroom_name":classroom_name
        },
        success : function (result) {
            if (result.status === OPERATION_SUCCESS) {
                console.log("success");
            } else {
                alert("修改classroom_name 失败");
            }
        }
    });
    });
    $("input[name='"+name+"']").keyup(function(event){
         if(event.keyCode == 13){
             $(this).blur();
         }
    });
} 
