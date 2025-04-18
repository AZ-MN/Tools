import jsonpath

json_data = [
    {
        "afterFormData": {
            "bof_code_5fd34c08adaed6ba989927a7": 123,
            "bof_code_05c942a8956285c473bffc7a": "单行",
            "bof_code_modal_result": "确定",
            "bof_code_aa1540d98e7422f40dd6c558": "多行"
        },
        "afterTableData": {}
    }
]


# 使用jsonpath获取单行、数字、多行数据
def invoke():
    # 获取数据来源节点全部数据
    output = json_data
    # 处理数据1
    # data = json_data[0]["afterFormData"]
    # single_line = data["bof_code_05c942a8956285c473bffc7a"]
    # number = data["bof_code_5fd34c08adaed6ba989927a7"]
    # multi_line = data["bof_code_aa1540d98e7422f40dd6c558"]
    # output_json = {
    #     "single_line": single_line,
    #     "number": number,
    #     "multi_line": multi_line
    # }
    #
    # return output_json

    # 处理数据2
    result = {}
    for item in output:
        after_form_data = item["afterFormData"]
        for key, value in after_form_data.items():
            result[key] = value

    return result


if __name__ == '__main__':
    print(invoke())
