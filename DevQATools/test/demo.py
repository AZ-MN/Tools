# -*- coding: utf-8 -*-
"""
@File    : demo.py
@Time    : 2025/9/18 17:22
@Author  : Ning.M
@Version : 1.0
@Description : 
"""


import os
import sys

CONFIG_FILENAME = "webhooks_config.json"

# 在代码中添加以下调试代码来查看实际路径
if hasattr(sys, '_MEIPASS'):
    # 打包后的环境
    config_dir = os.path.expanduser("~")
    config_file = os.path.join(config_dir, f".{CONFIG_FILENAME}")
else:
    # 开发环境
    config_file = CONFIG_FILENAME

print(f"配置文件路径: {config_file}")