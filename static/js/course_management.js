function add_class_input(){
    $(".class_ul").prepend('<li><input class="classroom_name" type="text"></li>');
}
function submit_course(){
    var tempArr = [], res;
    $(".classroom_name").each(function(){
        tempArr.push($(this).val());
    })
    res = tempArr.join(";");
    $("#classroom_name_string").val(res);
    console.log($("#classroom_name_string").val());
    $("#create_course_form").submit();
}
