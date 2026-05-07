import sys
import os
import math
import platform
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QLineEdit, QPushButton
)


def resource_path(relative_path):
    """将相对路径转换为绝对路径（兼容开发环境和打包环境）"""
    if getattr(sys, 'frozen', False):  # 检查是否运行在PyInstaller打包环境中
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class CalculatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计算器")
        self.setGeometry(300, 300, 360, 500)
        self.setMinimumSize(360, 500)

        # 设置窗口图标 - 兼容开发环境和打包环境
        icon_path = resource_path("calculator.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"警告: 图标文件未找到 - {icon_path}")

        # 精确匹配图片的配色方案
        self.color_theme = {
            'display_bg': "#ffffff",
            'display_text': "#000000",
            'function_btn': "#f1f3f4",
            'function_text': "#202124",
            'number_btn': "#ffffff",
            'number_text': "#202124",
            'operator_btn': "#4285f4",
            'operator_text': "#ffffff",
            'equal_btn': "#4285f4",
            'equal_text': "#ffffff",
            'border': "#f1f3f4",
            'clear_btn': "#f8e7e7",
            'clear_text': "#d93025"
        }

        self.setup_ui()
        self.apply_styles()
        self.reset_calculator()

    def setup_ui(self):
        """设置界面组件 - 精确匹配图片布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 显示屏 - 精确图片样式
        self.display = QLineEdit('0')
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True)
        self.display.setFocusPolicy(Qt.NoFocus)
        self.display.setMinimumHeight(80)
        self.display.setFont(QFont("Arial", 32))
        self.display.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.color_theme['display_bg']};
                color: {self.color_theme['display_text']};
                border: 1px solid {self.color_theme['border']};
                border-radius: 8px;
                font-size: 32px;
                padding: 0 15px;
            }}
        """)
        main_layout.addWidget(self.display)

        # 主按钮网格（5行4列布局）- 精确图片样式
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(8)  # 按钮水平间距
        grid_layout.setVerticalSpacing(8)  # 按钮垂直间距

        # 按钮文本按行组织 - 精确匹配图片布局
        buttons = [
            ['♫', 'AC', '←', '÷'],  # 第一行：清零、空、退格、除法
            ['7', '8', '9', '×'],  # 第二行：7、8、9、乘法
            ['4', '5', '6', '-'],  # 第三行：4、5、6、减法
            ['1', '2', '3', '+'],  # 第四行：1、2、3、加法
            ['±', '0', '.', '=']  # 第五行：正负号、0、小数点、等号
        ]

        # 创建按钮并添加到网格 - 居中显示文本
        self.buttons = {}
        for row, row_buttons in enumerate(buttons):
            for col, text in enumerate(row_buttons):
                if not text:  # 跳过空按钮
                    continue

                btn = QPushButton(text)
                btn.setMinimumSize(70, 60)  # 统一按钮高度为60px

                # 根据文本类型设置不同字体
                if text in ['÷', '×', '-', '+', '=']:
                    btn.setFont(QFont("Arial", 16, QFont.Bold))
                elif text in ['←', 'AC']:
                    btn.setFont(QFont("Arial", 14))
                else:
                    btn.setFont(QFont("Arial", 16, QFont.Normal))

                # 设置按钮类型用于样式
                if text in ['÷', '×', '-', '+']:
                    btn.setProperty('class', 'operator')
                elif text == '=':
                    btn.setProperty('class', 'equal')
                elif text in ['AC', '←']:
                    btn.setProperty('class', 'clear')
                else:
                    btn.setProperty('class', 'number')

                grid_layout.addWidget(btn, row, col)
                self.buttons[(row, col)] = btn

                # 连接信号
                btn.clicked.connect(self.on_button_click)

        main_layout.addLayout(grid_layout)

    def apply_styles(self):
        """应用样式表 - 精确匹配图片样式"""
        theme = self.color_theme

        style = f"""
            QPushButton {{
                border-radius: 4px;
                font-weight: 500;
                border: 1px solid {theme['border']};
            }}

            QPushButton:pressed {{
                background-color: #e8e8e8;
            }}

            QPushButton[class="number"] {{
                background-color: {theme['number_btn']};
                color: {theme['number_text']};
            }}

            QPushButton[class="number"]:hover {{
                background-color: #f8f9fa;
            }}

            QPushButton[class="operator"] {{
                background-color: {theme['operator_btn']};
                color: {theme['operator_text']};
            }}

            QPushButton[class="operator"]:hover {{
                background-color: #3367d6;
            }}

            QPushButton[class="equal"] {{
                background-color: {theme['equal_btn']};
                color: {theme['equal_text']};
            }}

            QPushButton[class="equal"]:hover {{
                background-color: #3367d6;
            }}

            QPushButton[class="clear"] {{
                background-color: {theme['clear_btn']};
                color: {theme['clear_text']};
            }}

            QPushButton[class="clear"]:hover {{
                background-color: #f9d9d9;
            }}
        """
        self.setStyleSheet(style)

    def reset_calculator(self):
        """重置计算器状态"""
        self.current_value = '0'
        self.stored_value = None
        self.operator = None
        self.is_new_value = True
        self.display.setText('0')

    def on_button_click(self):
        """处理按钮点击事件"""
        button = self.sender()
        text = button.text()

        # 处理数字按钮
        if text in '0123456789':
            self.handle_digit(text)

        # 处理小数点
        elif text == '.':
            self.handle_decimal()

        # 处理正负号转换
        elif text == '±':
            self.toggle_sign()

        # 处理运算符
        elif text in ['+', '-', '×', '÷']:
            self.handle_operator(text)

        # 处理等号
        elif text == '=':
            self.calculate_result()

        # 处理退格
        elif text == '←':
            self.handle_backspace()

        # 处理清零
        elif text == 'AC':
            self.reset_calculator()

    def handle_digit(self, digit):
        """处理数字输入"""
        if self.current_value == '0' or self.is_new_value:
            self.current_value = digit
            self.is_new_value = False
        else:
            if len(self.current_value) < 12:  # 限制最大长度
                self.current_value += digit

        self.display.setText(self.current_value)

    def handle_decimal(self):
        """处理小数点输入"""
        if '.' not in self.current_value:
            if self.is_new_value:
                self.current_value = '0.'
                self.is_new_value = False
            else:
                self.current_value += '.'
            self.display.setText(self.current_value)

    def toggle_sign(self):
        """转换数字的正负号"""
        if self.current_value.startswith('-'):
            self.current_value = self.current_value[1:]
        else:
            if self.current_value != '0':
                self.current_value = '-' + self.current_value

        self.display.setText(self.current_value)

    def handle_operator(self, operator):
        """处理运算符"""
        # 如果有未完成的运算，先计算
        if self.stored_value is not None and not self.is_new_value:
            self.calculate_result()

        self.stored_value = float(self.current_value)
        self.operator = operator
        self.is_new_value = True

    def handle_backspace(self):
        """处理退格键"""
        if self.current_value == '0' or self.is_new_value:
            return

        # 删除最后一个字符
        self.current_value = self.current_value[:-1]
        if not self.current_value or self.current_value == '-':
            self.current_value = '0'
            self.is_new_value = True

        self.display.setText(self.current_value)

    def calculate_result(self):
        """执行计算并显示结果"""
        if self.stored_value is None or self.operator is None or self.is_new_value:
            return

        try:
            current = float(self.current_value)

            if self.operator == '+':
                result = self.stored_value + current
            elif self.operator == '-':
                result = self.stored_value - current
            elif self.operator == '×':
                result = self.stored_value * current
            elif self.operator == '÷':
                if current == 0:
                    self.display.setText('错误')
                    self.stored_value = None
                    self.current_value = '0'
                    self.is_new_value = True
                    return
                result = self.stored_value / current

            self.set_result(result)
            self.stored_value = result

        except Exception as e:
            self.display.setText('错误')
            self.reset_calculator()

    def set_result(self, result):
        """设置计算结果"""
        # 格式化为字符串显示
        result_str = f"{result:.8f}"
        result_str = result_str.rstrip('0').rstrip('.')
        if not result_str:  # 如果结果是0且所有小数位都是0
            result_str = '0'

        self.display.setText(result_str)
        self.current_value = result_str
        self.is_new_value = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置全局字体 - 确保所有组件都使用相同的字体
    app.setFont(QFont("Arial", 10))

    # 在macOS上修复图标显示问题
    if platform.system() == "Darwin":
        os.environ["QT_MAC_WANTS_LAYER"] = "1"

    calculator = CalculatorApp()
    calculator.show()
    sys.exit(app.exec_())