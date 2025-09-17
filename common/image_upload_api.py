# -*- coding: utf-8 -*-
"""
@File    : image_upload_api.py
@Time    : 2025/9/17 16:24
@Author  : Ning.M
@Version : 1.0
@Description : 上传文件并返回base64和MD5
"""
from flask import Flask, request, jsonify
import base64
import hashlib
from io import BytesIO

app = Flask(__name__)

# 配置上传文件的最大大小为10MB
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024


def calculate_md5(file_content):
    """计算文件内容的MD5值"""
    md5_hash = hashlib.md5()
    md5_hash.update(file_content)
    return md5_hash.hexdigest()


def image_to_base64(image_content):
    """将图片内容转换为base64编码"""
    return base64.b64encode(image_content).decode('utf-8')


@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        # 检查是否有文件部分
        if 'file' not in request.files:
            return jsonify({'error': '未找到文件'}), 400

        file = request.files['file']

        # 检查文件名是否为空
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        # 检查文件是否存在且是允许的类型
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            # 读取文件内容
            file_content = file.read()

            # 计算MD5
            md5_value = calculate_md5(file_content)

            # 转换为base64
            base64_str = image_to_base64(file_content)

            # 返回结果
            return jsonify({
                'success': True,
                'md5': md5_value,
                'base64': base64_str,
                'filename': file.filename,
                'message': '文件上传成功'
            })
        else:
            return jsonify({'error': '不支持的文件类型，仅支持图片文件'}), 400

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


if __name__ == '__main__':
    # 更换端口为未被占用的端口，关闭调试模式
    app.run(host='0.0.0.0', port=5001)
