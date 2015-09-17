var OPERATION_SUCCESS = 1,
    OPERATION_FAIL = 2,
    INIT = '11',
    RUNNING = '12',
    SUSPEND = '13',
    ERROR = '14';

$.ajaxSetup({
        type : "POST", url : "/course_meta/j", cache : false, dataType : "json"
});

function edit_tta_socket_submit(){
    var tta_id = $('#input_tta_name').attr('data-tta-id'),
        tta_socket_id = $('#input_tta_name').attr('data-tta-socket-id'),
        ip = $('#input_tta_ip').val(),
        port = $('#input_tta_ip_port').val();
    $.ajax({
        data : {
            "type":"edit_tta_socket", "tta_socket_id":tta_socket_id, "ip":ip, "port":port
        },
        success : function (result) {
            if (result.status === OPERATION_SUCCESS) {
                // TODO may be problem in status chagne
                $('#tta_socket_'+ tta_socket_id + ' td span').html(result.socket);
                $('input').val('');
                $('#add-tta-socket').modal('hide');
            } else {
                alert("修改TTA端口失败");
            }
        }
    });
}

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
     ///
    $.ajax({
        data : {
            "type":"change_course_name",
            "course_id":course_id,
            "course_name":course_name
        },
        success : function (result) {
            if (result.status === OPERATION_SUCCESS) {
                // TODO may be problem in status chagne
                console.log("success");
            } else {
                alert("修改course_name 失败");
            }
        }
    });
     ///
    });

    $("input[name='"+name+"']").keyup(function(event){
         if(event.keyCode == 13){
             $(this).blur();
         }
    });
} 
