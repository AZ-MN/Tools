var {
    JSONPath
} = require('jsonpath-plus');
var res = pm.response.json();
//检查单行输入
pm.test("检查单行输入日志正确", function () {
    var old_single_line = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="单行输入")].oldValue', json: res
    }).toString();
    pm.expect(old_single_line).to.eql(pm.variables.get("old_single_line"));

    var new_single_line = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="单行输入")].newValue', json: res
    }).toString();
    pm.expect(new_single_line).to.eql(pm.variables.get("new_single_line"));
});
//检查数字输入组件
pm.test("检查数字输入日志正确", function () {
    var old_number = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="数字输入")].oldValue', json: res
    }).toString();
    pm.expect(old_number).to.eql(pm.variables.get("old_number"));

    var new_number = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="数字输入")].newValue', json: res
    }).toString();
    pm.expect(new_number).to.eql(pm.variables.get("new_number"));
});

//检查单选框组件
pm.test("检查单选框日志正确", function () {
    var old_single_select = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="单选框")].oldValue', json: res
    }).toString();
    pm.expect(old_single_select).to.eql(pm.variables.get("old_single_select"));

    var new_single_select = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="单选框")].newValue', json: res
    }).toString();
    pm.expect(new_single_select).to.eql(pm.variables.get("new_single_select"));
});

//检查部门选择组件
pm.test("检查部门选择日志正确", function () {
    var old_dep = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="部门选择")].oldValue', json: res
    }).toString();
    pm.expect(old_dep).to.eql(pm.variables.get("old_dep"));

    var new_dep = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="部门选择")].newValue', json: res
    }).toString();
    pm.expect(new_dep).to.eql(pm.variables.get("new_dep"));
});

//检查数据选择组件
pm.test("检查部门选择日志正确", function () {
    var old_data_select = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="数据选择")].oldValue', json: res
    }).toString();
    pm.expect(old_data_select).to.eql(pm.variables.get("old_data_select"));

    var new_data_select = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="数据选择")].newValue', json: res
    }).toString();
    pm.expect(new_data_select).to.eql(pm.variables.get("new_data_select"));
});

//检查富文本组件
pm.test("检查富文本日志正确", function () {
    var old_rich_text = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="富文本")].oldValue', json: res
    }).toString();
    pm.expect(old_rich_text).to.eql(pm.variables.get("old_rich_text"));

    var new_rich_text = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="富文本")].newValue', json: res
    }).toString();
    pm.expect(new_rich_text).to.eql(pm.variables.get("new_rich_text"));
});

//检查开关组件
pm.test("检查开关日志正确", function () {
    var old_switch_button = JSONPath({
        path: '$.data.result[0]..[?(@.columnName=="开关")].oldValue', json: res
    }).toString();
    pm.expect(old_switch_button).to.eql(pm.variables.get("old_switch_button"));

    var new_switch_button = JSONPath({
        path: '$.data.result[0]..[?(@.columnName=="开关")].newValue',
        json: res
    }).toString();
    pm.expect(new_switch_button).to.eql(pm.variables.get("new_switch_button"));
});
var old_switch_button = JSONPath({path: '$.data.result[1]..[?(@.columnName=="开关")].oldValue', json: res}).toString();
var new_switch_button = JSONPath({path: '$.data.result[1]..[?(@.columnName=="开关")].newValue', json: res
}).toString();


//检查人员选择组件
pm.test("检查人员选择日志正确", function () {
    var old_person_select = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="人员选择")].oldValue', json: res
    }).toString();
    pm.expect(old_person_select).to.eql(pm.variables.get("old_person_select"));

    var new_person_select = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="人员选择")].newValue', json: res
    }).toString();
    pm.expect(new_person_select).to.eql(pm.variables.get("new_person_select"));
});

//检查地区地址组件
pm.test("检查地区地址日志正确", function () {
    // var old_address = JSONPath({ path: '$.data.result[1]..[?(@.columnName=="地区地址")].oldValue', json: res }).toString();
    // pm.expect(old_address).to.eql(pm.variables.get("old_address"));
    var new_address = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="地区地址")].newValue', json: res
    }).toString();
    pm.expect(new_address).to.eql(pm.variables.get("new_address"));
});

//检查多行输入
pm.test("检查多行输入日志正确", function () {
    var old_multi_line = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="多行输入")].oldValue', json: res
    }).toString();
    pm.expect(old_multi_line).to.eql(pm.variables.get("old_multi_line"));

    var new_multi_line = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="多行输入")].newValue', json: res
    }).toString();
    pm.expect(new_multi_line).to.eql(pm.variables.get("new_multi_line"));
});

//检查手机号码 phone
pm.test("检查手机号码日志正确", function () {
    var old_phone = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="手机号码")].oldValue', json: res
    }).toString();
    pm.expect(old_phone).to.eql(pm.variables.get("old_phone"));

    var new_phone = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="手机号码")].newValue', json: res
    }).toString();
    pm.expect(new_phone).to.eql(pm.variables.get("new_phone"));
});
//检查电子邮箱
pm.test("检查电子邮箱日志正确", function () {
    var old_mail = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="电子邮箱")].oldValue', json: res
    }).toString();
    pm.expect(old_mail).to.eql(pm.variables.get("old_mail"));

    var new_mail = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="电子邮箱")].newValue', json: res
    }).toString();
    pm.expect(new_mail).to.eql(pm.variables.get("new_mail"));
});
//检查证件号
pm.test("检查证件号日志正确", function () {
    var old_id_number = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="证件号")].oldValue', json: res
    }).toString();
    pm.expect(old_id_number).to.eql(pm.variables.get("old_id_number"));

    var new_id_number = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="证件号")].newValue', json: res
    }).toString();
    pm.expect(new_id_number).to.eql(pm.variables.get("new_id_number"));
});

//检查多选框
pm.test("检查多选框日志正确", function () {
    var old_checkbox = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="多选框")].oldValue', json: res
    }).toString();
    pm.expect(old_checkbox).to.eql(pm.variables.get("old_checkbox"));

    var new_checkbox = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="多选框")].newValue', json: res
    }).toString();
    pm.expect(new_checkbox).to.eql(pm.variables.get("new_checkbox"));
});
//检查下拉框
pm.test("检查下拉框日志正确", function () {
    var old_dropdown_option = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="下拉框")].oldValue', json: res
    }).toString();
    pm.expect(old_dropdown_option).to.eql(pm.variables.get("old_dropdown_option"));

    var new_dropdown_option = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="下拉框")].newValue', json: res
    }).toString();
    pm.expect(new_dropdown_option).to.eql(pm.variables.get("new_dropdown_option"));
});
//检查金额
pm.test("检查金额日志正确", function () {
    var old_amount = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="金额")].oldValue', json: res
    }).toString();
    pm.expect(old_amount).to.eql(pm.variables.get("old_amount"));

    var new_amount = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="金额")].newValue', json: res
    }).toString();
    pm.expect(new_amount).to.eql(pm.variables.get("new_amount"));
});

//检查附件上传
pm.test("检查附件上传日志正确", function () {
    var old_attachment = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="附件上传")].oldValue', json: res
    }).toString();
    pm.expect(old_attachment).to.include(pm.variables.get("old_attachment"));

    var new_attachment = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="附件上传")].newValue', json: res
    }).toString();
    pm.expect(new_attachment).to.include(pm.variables.get("new_attachment"));
});

//检查超链接
pm.test("检查超链接日志正确", function () {
    var old_hyperlink = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="超链接")].oldValue', json: res
    }).toString();
    pm.expect(old_hyperlink).to.eql(pm.variables.get("old_hyperlink"));

    var new_hyperlink = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="超链接")].newValue', json: res
    }).toString();
    pm.expect(new_hyperlink).to.eql(pm.variables.get("new_hyperlink"));
});

//检查他表字段
pm.test("检查他表字段日志正确", function () {
    var old_other_table_fields = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="他表字段")].oldValue', json: res
    }).toString();
    pm.expect(old_other_table_fields).to.eql(pm.variables.get("old_other_table_fields"));

    var new_other_table_fields = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="他表字段")].newValue', json: res
    }).toString();
    new_other_table_fields = new_other_table_fields[0];
    pm.expect(new_other_table_fields).to.eql(pm.variables.get("new_other_table_fields"));
});

//检查日期时间
pm.test("检查日期时间日志正确", function () {
    var old_date = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="日期时间")].oldValue', json: res
    }).toString();
    pm.expect(old_date).to.eql(pm.variables.get("old_date"));

    var new_date = JSONPath({
        path: '$.data.result[1]..[?(@.columnName=="日期时间")].newValue', json: res
    }).toString();
    pm.expect(new_date).to.eql(pm.variables.get("new_date"));
});
