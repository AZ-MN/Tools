# -*- coding: utf-8 -*-
"""
@File    : lark_get_image_key.py
@Time    : 2025/12/8 13:04
@Author  : Ning.M
@Version : 1.0
@Description : 
"""

import json

import lark_oapi as lark
from lark_oapi.api.im.v1 import *


# SDK 使用说明: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/preparations-before-development
# 以下示例代码默认根据文档示例值填充，如果存在代码问题，请在 API 调试台填上相关必要参数后再复制代码使用
# 复制该 Demo 后, 需要将 "YOUR_APP_ID", "YOUR_APP_SECRET" 替换为自己应用的 APP_ID, APP_SECRET.
def get_image_key():
    # 创建client
    client = lark.Client.builder() \
        .app_id("cli_a9bcf9b712f91bb3") \
        .app_secret("a5777UUYJAFHKq7qgUx5PffKrEs8x7M8") \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    # 构造请求对象
    file = open(r"D:\PythonCode\Tools\img\action.gif", "rb")
    request: CreateImageRequest = CreateImageRequest.builder() \
        .request_body(CreateImageRequestBody.builder()
            .image_type("message")
            .image(file)
            .build()) \
        .build()

    # 发起请求
    response: CreateImageResponse = client.im.v1.image.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.im.v1.image.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))
    return response.data.image_key
