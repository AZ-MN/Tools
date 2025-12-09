# -*- coding: utf-8 -*-
"""
@File    : 飞书消息推送.py
@Time    : 2025/12/8 11:19
@Author  : Ning.M
@Version : 1.0
@Description : 用于飞书机器人消息推送服务
"""

import requests
import json
from typing import Dict, Optional
from lark_get_image_key import get_image_key


class FeishuBot:
    """飞书机器人 Webhook 消息推送类"""

    def __init__(self, webhook_url: str):
        """
        初始化机器人
        :param webhook_url: 飞书机器人的 Webhook 地址
        """
        self.webhook_url = webhook_url
        self.headers = {"Content-Type": "application/json; charset=utf-8"}

    def send_text(self, content: str, at_all: bool = False, at_users: list = None) -> Dict:
        """
        发送纯文本消息
        :param content: 文本内容
        :param at_all: 是否@所有人
        :param at_users: 指定@的用户ID列表（如 ["ou_123456"]）
        :return: 接口响应结果
        """
        payload = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }
        # 处理@所有人
        if at_all:
            payload["content"]["text"] += " <at user_id='all'>所有人</at>"
        # 处理指定@用户
        if at_users and isinstance(at_users, list):
            for user_id in at_users:
                payload["content"]["text"] += f" <at user_id='{user_id}'></at>"
        return self._send_request(payload)

    def send_post(self, title: str, content: list) -> Dict:
        """
        发送富文本（Post）消息
        :param title: 标题
        :param content: 内容体（飞书Post格式，示例见调用示例）
        :return: 接口响应结果
        """
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh-CN": {
                        "title": title,
                        "content": content
                    }
                }
            }
        }
        return self._send_request(payload)

    def send_interactive_card(self, card: Dict) -> Dict:
        """
        发送交互式卡片消息（飞书卡片V2）
        :param card: 卡片配置（示例见调用示例）
        :return: 接口响应结果
        """
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        return self._send_request(payload)

    def _send_request(self, payload: Dict) -> Optional[Dict]:
        """
        通用发送请求方法（内部调用）
        :param payload: 消息体
        :return: 响应字典（失败返回None）
        """
        try:
            response = requests.post(
                url=self.webhook_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()  # 抛出HTTP异常
            result = response.json()
            if result.get("code") == 0:
                print(f"消息发送成功：{result}")
                return result
            else:
                print(f"消息发送失败：{result}")
                return result
        except requests.exceptions.RequestException as e:
            print(f"请求异常：{str(e)}")
            return None
        except json.JSONDecodeError:
            print("响应解析失败，非JSON格式")
            return None


# -------------------------- 调用示例 --------------------------
if __name__ == "__main__":
    # 飞书机器人Webhook地址
    WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/738d112d-c35e-4c27-a7b6-9da6ef28639a"

    # 初始化机器人
    bot = FeishuBot(WEBHOOK_URL)

    # 获取图片key
    image_key = get_image_key()
    print(f"图片key: {image_key}")

    # 1. 发送纯文本消息
    print("\n=== 发送纯文本消息 ===")
    # bot.send_text(
    #     content="这是一条纯文本测试消息📝",
    #     at_all=True,  # 设为True则@所有人
    #     at_users=["ou_xxxxxx"]  # 替换为实际用户ID（可选）
    # )

    # 2. 发送富文本（Post）消息
    print("\n=== 发送富文本消息 ===")
    post_content = [
        [{"tag": "text", "text": "富文本消息示例："}],
        [{"tag": "text", "text": "1. 普通文本"}],
        [{"tag": "a", "text": "2. 超链接示例", "href": "https://www.feishu.cn"}],
        [{"tag": "at", "text": "3. @指定用户", "user_id": "ou_xxxxxx"}],
        [{"tag": "img", "image_key": image_key, "width": 300, "height": 200}]  # 替换为实际图片key
    ]
    # bot.send_post(
    #     title="富文本消息标题",
    #     content=post_content
    # )

    # 3. 发送交互式卡片消息（常用）
    print("\n=== 发送交互式卡片消息 ===")
    card_content = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": "### 卡片消息示例\n这是一条飞书交互式卡片消息",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "按钮1", "tag": "plain_text"},
                        "type": "primary"
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "更多智能体"
                        },
                        "type": "default",
                        "width": "default",
                        "size": "medium",
                        "behaviors": [
                            {
                                "type": "open_url",
                                "default_url": "https://www.coze.cn/",
                                "pc_url": "",
                                "ios_url": "",
                                "android_url": ""
                            }
                        ],
                        "margin": "0px 0px 0px 0px"
                    }
                ]
            }
        ],
        "header": {
            "title": {"content": "卡片标题", "tag": "plain_text"},
            "template": "blue"
        }
    }
    bot.send_interactive_card(card=card_content)