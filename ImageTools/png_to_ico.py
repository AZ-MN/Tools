# convert_all_images_to_ico.py
from PIL import Image
import glob
import os


def convert_png_to_ico(png_path, ico_path, sizes=[16, 32, 48, 64, 128, 256]):
    """
    将PNG文件转换为高质量ICO图标
    """
    print(f"正在转换: {png_path} -> {ico_path}")

    # 创建不同尺寸的图像
    images = []
    for size in sizes:
        img = Image.open(png_path)
        img = img.resize((size, size), Image.LANCZOS)  # 高质量缩放
        images.append(img)

    # 保存为ICO文件
    images[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes])


if __name__ == "__main__":
    # 转换当前目录下所有PNG为ICO
    for png_file in glob.glob("*.png"):
        ico_file = os.path.splitext(png_file)[0] + ".ico"
        convert_png_to_ico(png_file, ico_file)

    print("所有PNG文件已转换为ICO格式")
