from flask import Flask, request, send_file
import cv2 as cv
import numpy as np
import os
import tempfile
import shutil
import imghdr

app = Flask(__name__)


def precise_watermark_removal(img_path):
    """
    四阶段精准去除方案：
    1. 多维度水印定位
    2. 智能蒙版增强
    3. 分层修复技术
    4. 边缘融合处理
    """
    try:
        img = cv.imread(img_path)
        if img is None:
            return None

        # 第一阶段：精准区域定位
        height, width = img.shape[:2]
        watermark_rect = (
            int(width * 0.92),  # 根据描述，水印在右下角8%位置
            int(height * 0.96),
            int(width * 0.995),
            int(height * 0.995)
        )
        x1, y1, x2, y2 = watermark_rect
        roi = img[y1:y2, x1:x2]

        # 第二阶段：多维度蒙版生成
        # 通道分离检测
        b, g, r = cv.split(roi)
        gray_roi = cv.cvtColor(roi, cv.COLOR_BGR2GRAY)

        # 自适应阈值处理
        adaptive_thresh = cv.adaptiveThreshold(gray_roi, 255,
                                               cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                                               cv.THRESH_BINARY, 11, 8)

        # 边缘强化检测
        edges = cv.Canny(gray_roi, 150, 250)

        # 多蒙版融合
        combined_mask = cv.bitwise_or(adaptive_thresh, edges)

        # 第三阶段：形态学优化
        kernel = cv.getStructuringElement(cv.MORPH_CROSS, (2, 2))
        refined_mask = cv.morphologyEx(combined_mask, cv.MORPH_CLOSE, kernel, iterations=2)

        # 第四阶段：分层修复技术
        full_mask = np.zeros_like(img[:, :, 0])
        full_mask[y1:y2, x1:x2] = refined_mask

        # 初级修复（背景重建）
        temp_result = cv.inpaint(img, full_mask, 3, cv.INPAINT_TELEA)

        # 精细修复（纹理恢复）
        final_result = cv.inpaint(temp_result, full_mask, 2, cv.INPAINT_NS)

        # 边缘融合处理
        blend_area = final_result[y1 - 3:y2 + 3, x1 - 3:x2 + 3]
        blended = cv.GaussianBlur(blend_area, (3, 3), 0)
        final_result[y1 - 3:y2 + 3, x1 - 3:x2 + 3] = cv.addWeighted(blend_area, 0.6, blended, 0.4, 0)

        return final_result

    except Exception as e:
        print(f"精准处理错误：{str(e)}")
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 文件验证部分
        if 'image' not in request.files:
            return "没有上传文件", 400

        file = request.files['image']
        if file.filename == '':
            return "未选择文件", 400

        # 安全验证
        allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}
        filename = file.filename.lower()
        if '.' not in filename or filename.rsplit('.', 1)[1] not in allowed_extensions:
            return "不支持的文件类型", 400

        try:
            # 验证实际文件内容
            file_stream = file.stream
            file_stream.seek(0)
            header = file_stream.read(1024)
            file_type = imghdr.what(None, header)
            if file_type not in allowed_extensions:
                return "无效的图片文件", 400
            file_stream.seek(0)
        except Exception as e:
            return f"文件验证失败：{str(e)}", 400

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(dir=os.getcwd())
        try:
            # 保存原始文件
            image_path = os.path.join(temp_dir, filename)
            with open(image_path, 'wb') as f:
                f.write(file_stream.read())

            # 处理水印
            processed_image = precise_watermark_removal(image_path)
            if processed_image is None:
                return "水印去除失败", 500

            # 保存并返回结果
            output_filename = f"Remove_watermark_{filename}"
            output_path = os.path.join(temp_dir, output_filename)

            if not cv.imwrite(output_path, processed_image):
                return "无法保存处理后的文件", 500

            return send_file(
                output_path,
                as_attachment=True,
                download_name=output_filename
            )

        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # 前端界面
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI水印去除工具</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 20px auto; 
                padding: 20px;
                background: #1a1a1a;
                color: #fff;
            }
            h1 { 
                color: #00ff9d;
                text-align: center;
                text-shadow: 0 0 10px rgba(0,255,157,0.5);
            }
            form { 
                background: #2d2d2d; 
                padding: 25px; 
                border-radius: 15px;
                box-shadow: 0 0 20px rgba(0,255,157,0.2);
                border: 1px solid #00ff9d;
            }
            input[type="file"] { 
                margin: 15px 0;
                padding: 10px;
                background: #3d3d3d;
                border: 1px solid #00ff9d;
                color: #fff;
                width: 95%;
            }
            input[type="submit"] {
                background: linear-gradient(45deg, #00ff9d, #00ccff);
                color: #000;
                padding: 15px 30px;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-weight: bold;
                transition: 0.3s;
                display: block;
                margin: 0 auto;
            }
            input[type="submit"]:hover {
                transform: scale(1.05);
                box-shadow: 0 0 20px rgba(0,255,157,0.5);
            }
        </style>
    </head>
    <body>
        <h1>AI水印去除工具</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="image" accept="image/*" required>
            <input type="submit" value="✨ 开始魔法去水印 ✨">
        </form>
    </body>
    </html>
    '''


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

