import os
import zipfile
import re

# 中文数字转阿拉伯数字映射表
num_map = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000
}


def chinese_to_arabic(chinese_num):
    """将连续的中文数字转换为阿拉伯数字，如 '十四' -> 14"""
    if not chinese_num:
        return ""

    result = 0
    temp = 0
    for char in chinese_num:
        if char in num_map:
            # 处理进位单位（十、百、千、万）
            if num_map[char] >= 10:
                if temp == 0:
                    temp = 1  # 处理单独的"十"，如"十"->10
                temp *= num_map[char]
                result += temp
                temp = 0
            else:
                # 累加个位数字
                temp += num_map[char]
    # 加上最后剩余的数字
    result += temp
    return str(result)


def fix_filename_encoding(zip_info):
    """修复ZIP文件内部文件名的乱码问题"""
    raw_name = zip_info.filename

    # 尝试常见编码组合解决乱码
    encodings = [('cp437', 'utf-8'), ('cp437', 'gbk'), ('cp437', 'gb2312'), ('utf-8', 'utf-8')]
    for source_enc, target_enc in encodings:
        try:
            return raw_name.encode(source_enc).decode(target_enc)
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

    # 所有编码尝试失败时的兜底方案
    return raw_name.encode('cp437', errors='replace').decode('utf-8', errors='replace')


def process_lesson_filename(filename):
    """处理文件名，仅将'第X天课'中的中文数字X转换为阿拉伯数字，保留其他所有字符"""
    # 匹配"第[中文数字]天课"格式的模式
    pattern = re.compile(r'(第)([零一二三四五六七八九十百千万]+)(天课)')

    # 找到所有匹配的部分并替换
    def replace_num(match):
        # 保留"第"和"天课"，只替换中间的数字部分
        return match.group(1) + chinese_to_arabic(match.group(2)) + match.group(3)

    # 只替换符合"第X天课"格式的部分，其他内容保持不变
    return pattern.sub(replace_num, filename)


def extract_lesson_archives():
    # 配置路径
    source_dir = r"C:\Users\11583\Downloads"  # 压缩包所在目录
    target_base_dir = r"E:\码尚教育测试开发\Python全栈自动化测试系列课"  # 解压目标目录

    # 确保目标目录存在
    os.makedirs(target_base_dir, exist_ok=True)

    # 获取所有ZIP压缩包
    zip_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.zip')]

    if not zip_files:
        print("在源目录中未找到任何ZIP压缩包")
        return

    # 处理每个压缩包
    for zip_file in zip_files:
        zip_path = os.path.join(source_dir, zip_file)
        zip_base_name = os.path.splitext(zip_file)[0]

        # 处理压缩包名称，生成对应的文件夹名（保留完整的"第多少天课"格式）
        folder_name = process_lesson_filename(zip_base_name)
        full_target_dir = os.path.join(target_base_dir, folder_name)
        os.makedirs(full_target_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for file_info in zf.infolist():
                    # 修复文件名乱码
                    decoded_name = fix_filename_encoding(file_info)

                    # 处理内部文件/文件夹名，同样保留完整格式
                    processed_name = process_lesson_filename(decoded_name)
                    file_info.filename = processed_name

                    # 确保目标文件夹存在
                    target_path = os.path.join(full_target_dir, processed_name)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    # 解压文件
                    zf.extract(file_info, full_target_dir)
                    print(f"成功解压: {processed_name} -> {full_target_dir}")

        except zipfile.BadZipFile:
            print(f"错误: {zip_file} 不是有效的ZIP文件，已跳过")
        except Exception as e:
            print(f"处理 {zip_file} 时出错: {str(e)}，已跳过")

    print("所有压缩包处理完成")


if __name__ == "__main__":
    extract_lesson_archives()
