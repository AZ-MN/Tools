from flask import Flask, request, send_file
import cv2
import numpy as np
import os

app = Flask(__name__)


# 定义工具函数用于去除图片水印（简单示例，利用图像修复）
def remove_watermark(image_path):
    img = cv2.imread(image_path)
    # 这里假设水印区域是白色（你可能需要根据实际水印颜色等调整）
    mask = np.all(img == [255, 255, 255], axis=-1).astype(np.uint8) * 255
    # 使用图像修复算法来填充水印区域（Telea算法示例）
    result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    return result


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 检查是否有文件上传
        if 'image' not in request.files:
            return "No image file uploaded", 400
        file = request.files['image']
        if file.filename == '':
            return "No selected file", 400
        # 保存上传的图片到临时文件夹（创建临时文件夹如果不存在）
        if not os.path.exists('temp'):
            os.makedirs('temp')
        image_path = os.path.join('temp', file.filename)
        file.save(image_path)
        # 去除水印
        result_image = remove_watermark(image_path)
        # 保存处理后的图片到临时文件夹
        output_path = os.path.join('temp', 'output_' + file.filename)
        cv2.imwrite(output_path, result_image)
        # 返回处理后的图片供下载
        return send_file(output_path, as_attachment=True)
    return '''
    <!doctype html>
    <html>
    <body>
    <h1>图片去除水印工具</h1>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="image">
      <input type="submit" value="上传并去除水印">
    </form>
    </body>
    </html>
    '''


if __name__ == '__main__':
    app.run(debug=True)
