import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import requests
import base64
import hashlib
import threading
import json
import os

# 全局配置：Webhook持久化存储文件
CONFIG_FILE = "../webhooks_config.json"


class WeChatRobotSender:
    def __init__(self, root):
        self.root = root
        self.root.title("企业微信机器人消息推送")
        self.root.geometry("850x650")

        # ========== 关键修复1：用ttk.Style定义全局字体样式（兼容所有ttk组件） ==========
        self.style = ttk.Style()
        # 配置所有ttk组件的默认字体（SimHei 10号）
        self.style.configure(".", font=("SimHei", 10))
        # 单独加强标题字体（如Webhook列表标题、消息内容标题）
        self.style.configure("Title.TLabel", font=("SimHei", 11, "bold"))
        # 配置按钮字体（确保和其他组件统一）
        self.style.configure("TButton", font=("SimHei", 10))

        # 初始化数据（UI创建后再加载）
        self.webhooks = {}
        self.current_webhook = None
        self.selected_image = None
        self.image_path = None

        # Markdown默认模板
        self.DEFAULT_MARKDOWN_TEMPLATE = """# 企微消息 Markdown 格式示范
## 一、标题用法（# 越多级别越低，最多6级）

## 二、引用用法（开头用“> ”）
> 这是引用内容，常用于备注、说明文字

## 三、图片用法（仅支持网络图片，格式：![描述](URL)）
![示例图片](https://picsum.photos/800/400)

## 四、@用户用法
- @特定用户：<@13800138000>（替换为目标用户手机号）
- @所有人：<@all>（仅群机器人支持）

## 五、其他常用格式
- 加粗文本：**这是加粗内容**
- 链接：[点击访问百度](https://www.baidu.com)
"""

        # ========== 第一步：创建所有UI组件（移除所有ttk组件的font参数） ==========
        # 左侧：Webhook列表与操作
        left_frame = ttk.Frame(root, width=240)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # 用自定义Title样式（加粗）
        ttk.Label(left_frame, text="Webhook 列表", style="Title.TLabel").pack(anchor=tk.W, pady=3)
        # 原生tk组件（Listbox）保留font参数
        self.webhook_list = tk.Listbox(left_frame, font=("SimHei", 10))
        self.webhook_list.pack(fill=tk.BOTH, expand=True, pady=5)
        self.webhook_list.bind('<<ListboxSelect>>', self.on_webhook_select)

        # 左侧ttk按钮（已通过Style配置字体，无需传font）
        ttk.Button(left_frame, text="添加 Webhook", command=self.add_webhook).pack(fill=tk.X, pady=3)
        ttk.Button(left_frame, text="编辑 Webhook", command=self.edit_webhook).pack(fill=tk.X, pady=3)
        ttk.Button(left_frame, text="删除 Webhook", command=self.delete_webhook).pack(fill=tk.X, pady=3)
        ttk.Button(left_frame, text="测试连接", command=self.test_webhook).pack(fill=tk.X, pady=3)

        # 右侧：消息编辑与预览
        right_frame = ttk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 当前Webhook状态（ttk.Label，Style已配置字体）
        self.webhook_status = ttk.Label(right_frame, text="请选择一个 Webhook", foreground="#86909c")
        self.webhook_status.pack(anchor=tk.W, pady=3)

        # Markdown消息标题（用Title样式）
        ttk.Label(right_frame, text="Markdown 消息内容", style="Title.TLabel").pack(anchor=tk.W, pady=3)
        # 原生tk组件（Text）保留font参数
        self.msg_text = tk.Text(right_frame, height=12, font=("SimHei", 10))
        self.msg_text.pack(fill=tk.BOTH, expand=True, pady=3)

        # 模板按钮（ttk.Button，Style配置字体）
        template_frame = ttk.Frame(right_frame)
        template_frame.pack(fill=tk.X, pady=3)
        ttk.Button(template_frame, text="加载模板", command=self.load_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(template_frame, text="重置模板", command=self.reset_template).pack(side=tk.LEFT, padx=3)

        # @用户区域（ttk组件用Style字体，tk.Checkbutton保留font）
        at_frame = ttk.Frame(right_frame)
        at_frame.pack(fill=tk.X, pady=3)
        ttk.Label(at_frame, text="@用户（手机号，多个用逗号分隔）:").pack(side=tk.LEFT)
        # ttk.Entry（Style配置字体）
        self.at_entry = ttk.Entry(at_frame)
        self.at_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        self.at_all_var = tk.BooleanVar()
        # 原生tk.Checkbutton保留font
        tk.Checkbutton(at_frame, text="@所有人", variable=self.at_all_var, font=("SimHei", 10)).pack(side=tk.LEFT)

        # 图片选择区域（ttk组件用Style字体）
        img_frame = ttk.Frame(right_frame)
        img_frame.pack(fill=tk.X, pady=3)
        self.img_label = ttk.Label(img_frame, text="未选择图片（可选，本地图片单独发送）", foreground="#86909c")
        self.img_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(img_frame, text="选择图片", command=self.select_image).pack(side=tk.LEFT, padx=3)
        ttk.Button(img_frame, text="清除图片", command=self.clear_image).pack(side=tk.LEFT, padx=3)

        # 图片预览区域（ttk.Label）
        self.img_preview = ttk.Label(right_frame, borderwidth=1, relief="solid")
        self.img_preview.pack(fill=tk.BOTH, expand=True, pady=5)

        # 状态与发送按钮（ttk组件用Style字体）
        status_frame = ttk.Frame(right_frame)
        status_frame.pack(fill=tk.X, pady=3)
        self.status_label = ttk.Label(status_frame, text="状态：就绪", foreground="#86909c")
        self.status_label.pack(side=tk.LEFT)
        # 关键修复2：ttk.Button移除font参数，用Style配置
        self.send_btn = ttk.Button(status_frame, text="发送消息", command=self.send_message, state=tk.DISABLED)
        self.send_btn.pack(side=tk.RIGHT, padx=3)

        # ========== 第二步：加载Webhook数据并更新状态 ==========
        self.webhooks, load_status = self.load_webhooks_from_file()
        self.status_label.config(text=load_status, foreground="#008000")
        self.refresh_webhook_list()

    # ========== Webhook持久化：加载/保存 ==========
    def load_webhooks_from_file(self):
        """从本地JSON文件加载Webhook，返回（数据字典，状态提示文本）"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data, f"状态：加载{len(data)}条Webhook记录"
                else:
                    messagebox.showwarning("数据格式错误", "配置文件格式异常，将重新创建")
                    return {}, "状态：配置文件异常，已重新创建"
            except Exception as e:
                messagebox.showerror("加载失败", f"读取配置文件出错：{str(e)}，将重新创建")
                return {}, f"状态：加载失败，已重新创建配置文件"
        else:
            # 首次运行，创建空配置文件
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}, "状态：首次运行，创建配置文件"

    def save_webhooks_to_file(self):
        """将Webhook记录保存到本地JSON文件，返回是否成功"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.webhooks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("保存失败", f"写入配置文件出错：{str(e)}")
            return False

    # ========== 加宽添加Webhook弹窗（ttk组件用Style字体） ==========
    def add_webhook(self):
        """添加Webhook弹窗：增大尺寸+优化布局"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加 Webhook")
        dialog.geometry("600x280")  # 增大弹窗尺寸
        dialog.resizable(True, True)  # 禁止调整大小
        self.center_dialog(dialog)  # 保持居中
        dialog.transient(self.root)
        dialog.grab_set()

        # 内部Frame：减小padding，释放空间
        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Webhook名称：标签+输入框
        ttk.Label(frame, text="Webhook名称:").grid(row=0, column=0, sticky=tk.W, pady=8)
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=8, ipady=3)
        frame.columnconfigure(1, weight=1)  # 输入框随列拉伸

        # Webhook地址：标签+输入框
        ttk.Label(frame, text="Webhook地址:").grid(row=1, column=0, sticky=tk.W, pady=8)
        url_entry = ttk.Entry(frame)
        url_entry.grid(row=1, column=1, sticky=tk.EW, pady=8, ipady=3)

        # 按钮区域：确保“确定”“取消”都显示
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=tk.E)
        # 修复：确保save_webhook方法存在且参数正确
        ttk.Button(
            btn_frame,
            text="确定",
            command=lambda: self.save_webhook(dialog, name_entry.get(), url_entry.get())
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)

        name_entry.focus_set()  # 默认聚焦名称输入框

    def save_webhook(self, dialog, name, url):
        """保存Webhook的核心逻辑（确保方法存在）"""
        if not (name and url):
            messagebox.showwarning("输入错误", "名称和Webhook地址不能为空！")
            return
        if name in self.webhooks:
            messagebox.showwarning("重复错误", f"已存在名为「{name}」的Webhook！")
            return
        # 保存到内存+本地文件
        self.webhooks[name] = url
        self.webhook_list.insert(tk.END, name)
        self.save_webhooks_to_file()
        dialog.destroy()
        messagebox.showinfo("添加成功", f"Webhook「{name}」已保存")

    # ========== 编辑Webhook：显示之前的值（ttk组件用Style字体） ==========
    def edit_webhook(self):
        if not self.current_webhook:
            messagebox.showinfo("提示", "请先选择一个Webhook")
            return
        current_url = self.webhooks.get(self.current_webhook, "")
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑 Webhook")
        dialog.geometry("600x260")  # 匹配添加弹窗尺寸
        dialog.resizable(True, True)
        self.center_dialog(dialog)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Webhook名称:").grid(row=0, column=0, sticky=tk.W, pady=8)
        name_label = ttk.Label(frame, text=self.current_webhook, foreground="#0066cc", font=("SimHei", 10, "bold"))
        name_label.grid(row=0, column=1, sticky=tk.W, pady=8)

        ttk.Label(frame, text="Webhook地址:").grid(row=1, column=0, sticky=tk.W, pady=8)
        url_entry = ttk.Entry(frame, textvariable=tk.StringVar(value=current_url))
        url_entry.grid(row=1, column=1, sticky=tk.EW, pady=8, ipady=3)
        frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=tk.E)
        ttk.Button(
            btn_frame,
            text="确定",
            command=lambda: self.update_webhook(dialog, url_entry.get())
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)

        url_entry.focus_set()
        url_entry.select_range(0, tk.END)

    # ========== 其他原有功能（保持不变，仅确保ttk组件无font参数） ==========
    def delete_webhook(self):
        if not self.current_webhook:
            messagebox.showinfo("提示", "请先选择一个Webhook")
            return
        if messagebox.askyesno("确认删除", f"确定要删除Webhook「{self.current_webhook}」吗？删除后不可恢复"):
            del self.webhooks[self.current_webhook]
            if self.save_webhooks_to_file():
                self.current_webhook = None
                self.refresh_webhook_list()
                self.webhook_status.config(text="请选择一个 Webhook", foreground="#86909c")
                self.send_btn.config(state=tk.DISABLED)
                self.status_label.config(text="状态：Webhook已删除", foreground="#008000")
                messagebox.showinfo("删除成功", "Webhook已删除并同步到文件")

    def test_webhook(self):
        if not self.current_webhook:
            messagebox.showinfo("提示", "请先选择一个Webhook")
            return

        webhook_url = self.webhooks[self.current_webhook]
        self.status_label.config(text="状态：正在测试连接...", foreground="#ff8c00")
        self.root.update()

        def test():
            try:
                test_data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": "# Webhook测试成功\n这是一条测试消息，说明Webhook可正常使用！\n<@all>"
                    }
                }
                response = requests.post(webhook_url, json=test_data, timeout=10)
                response.raise_for_status()
                result = response.json()
                if result.get("errcode") == 0:
                    self.status_label.config(text="状态：测试连接成功", foreground="#008000")
                    messagebox.showinfo("测试成功", "Webhook连接正常，已发送测试消息（@所有人）")
                else:
                    err_msg = result.get("errmsg", "未知错误")
                    self.status_label.config(text=f"状态：测试失败 - {err_msg}", foreground="#ff0000")
                    messagebox.showerror("测试失败", f"企微API错误：{err_msg}（错误码：{result.get('errcode')}）")
            except requests.exceptions.Timeout:
                self.status_label.config(text="状态：测试失败 - 连接超时", foreground="#ff0000")
                messagebox.showerror("测试失败", "连接超时，请检查Webhook URL或网络")
            except requests.exceptions.RequestException as e:
                self.status_label.config(text=f"状态：测试失败 - {str(e)}", foreground="#ff0000")
                messagebox.showerror("测试失败", f"网络错误：{str(e)}")

        threading.Thread(target=test, daemon=True).start()

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if file_path:
            self.image_path = file_path
            display_name = file_path if len(file_path) < 50 else "..." + file_path[-50:]
            self.img_label.config(text=f"已选择：{display_name}", foreground="#000")
            try:
                img = Image.open(file_path)
                img.thumbnail((500, 300))
                self.selected_image = ImageTk.PhotoImage(img)
                self.img_preview.config(image=self.selected_image)
            except Exception as e:
                messagebox.showerror("预览失败", f"图片加载错误：{str(e)}")
                self.clear_image()

    def clear_image(self):
        self.image_path = None
        self.img_label.config(text="未选择图片（可选，本地图片单独发送）", foreground="#86909c")
        self.img_preview.config(image="")
        self.selected_image = None

    def send_message(self):
        if not self.current_webhook:
            messagebox.showinfo("提示", "请先选择一个Webhook")
            return

        msg_content = self.msg_text.get("1.0", tk.END).strip()
        if not msg_content:
            messagebox.showwarning("内容为空", "请输入Markdown消息内容")
            return

        mentioned_mobiles = []
        if self.at_all_var.get():
            mentioned_mobiles.append("all")
            msg_content += "\n<@all>"
        at_users = self.at_entry.get().strip().split(",") if self.at_entry.get().strip() else []
        for phone in at_users:
            phone = phone.strip()
            if phone and phone != "all":
                mentioned_mobiles.append(phone)
                msg_content += f"\n<@{phone}>"

        webhook_url = self.webhooks[self.current_webhook]
        self.send_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态：正在发送消息...", foreground="#ff8c00")
        self.root.update()

        def send():
            try:
                # 发送Markdown
                markdown_data = {
                    "msgtype": "markdown",
                    "markdown": {"content": msg_content},
                    "mentioned_mobile_list": mentioned_mobiles
                }
                md_response = requests.post(webhook_url, json=markdown_data, timeout=10)
                md_response.raise_for_status()
                md_result = md_response.json()
                if md_result.get("errcode") != 0:
                    raise Exception(f"Markdown发送失败：{md_result.get('errmsg')}（错误码：{md_result.get('errcode')}）")

                # 发送图片
                if self.image_path and os.path.exists(self.image_path):
                    with open(self.image_path, "rb") as f:
                        img_bytes = f.read()
                        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                        img_md5 = hashlib.md5(img_bytes).hexdigest()
                    img_data = {
                        "msgtype": "image",
                        "image": {"base64": img_base64, "md5": img_md5}
                    }
                    img_response = requests.post(webhook_url, json=img_data, timeout=10)
                    img_response.raise_for_status()
                    img_result = img_response.json()
                    if img_result.get("errcode") != 0:
                        raise Exception(f"图片发送失败：{img_result.get('errmsg')}（错误码：{img_result.get('errcode')}）")

                self.status_label.config(text="状态：消息发送成功", foreground="#008000")
                msg = "Markdown消息已发送" + ("和图片" if self.image_path else "")
                messagebox.showinfo("发送成功", msg)
            except Exception as e:
                self.status_label.config(text=f"状态：发送失败 - {str(e)}", foreground="#ff0000")
                messagebox.showerror("发送失败", f"错误原因：{str(e)}")
            finally:
                self.send_btn.config(state=tk.NORMAL)

        threading.Thread(target=send, daemon=True).start()

    def load_template(self):
        self.msg_text.delete("1.0", tk.END)
        self.msg_text.insert("1.0", self.DEFAULT_MARKDOWN_TEMPLATE)
        self.status_label.config(text="状态：模板已加载", foreground="#008000")

    def reset_template(self):
        if messagebox.askyesno("确认重置", "确定要恢复默认模板吗？当前内容将被覆盖"):
            self.load_template()

    def on_webhook_select(self, event):
        selection = self.webhook_list.curselection()
        if selection:
            self.current_webhook = self.webhook_list.get(selection[0])
            # 选中后标题加粗（单独设置font）
            self.webhook_status.config(text=f"当前选中：{self.current_webhook}", foreground="#000",
                                       font=("SimHei", 10, "bold"))
            self.send_btn.config(state=tk.NORMAL)
        else:
            self.current_webhook = None
            self.webhook_status.config(text="请选择一个 Webhook", foreground="#86909c")
            self.send_btn.config(state=tk.DISABLED)

    def refresh_webhook_list(self):
        self.webhook_list.delete(0, tk.END)
        for name in self.webhooks:
            self.webhook_list.insert(tk.END, name)

    def center_dialog(self, dialog):
        self.root.update_idletasks()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        dialog_w = dialog.winfo_reqwidth()
        dialog_h = dialog.winfo_reqheight()
        dialog_x = root_x + (root_w - dialog_w) // 2
        dialog_y = root_y + (root_h - dialog_h) // 2
        dialog.geometry(f"{dialog_w}x{dialog_h}+{dialog_x}+{dialog_y}")


if __name__ == "__main__":
    root = tk.Tk()
    app = WeChatRobotSender(root)
    root.mainloop()