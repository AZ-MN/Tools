import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import requests
import base64
import hashlib
import threading
import json
import os
import sys

# 配置文件名（持久化Webhook）
CONFIG_FILENAME = "webhooks_config.json"


class WeChatRobotSender:
    def __init__(self, root):
        self.root = root
        self.root.title("企业微信机器人消息推送")
        self.root.geometry("850x650")

        # 全局样式配置
        self.style = ttk.Style()
        self.style.configure(".", font=("SimHei", 10))
        self.style.configure("Title.TLabel", font=("SimHei", 11, "bold"))
        self.style.configure("TButton", font=("SimHei", 10))

        # 初始化数据
        self.webhooks = {}
        self.current_webhook = None
        self.selected_image = None
        self.image_path = None
        self.msg_type_var = tk.StringVar(value="Markdown")  # 默认消息类型

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

        # ========== UI组件创建 ==========
        # 左侧：Webhook列表与操作
        left_frame = ttk.Frame(root, width=240)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        ttk.Label(left_frame, text="Webhook 列表", style="Title.TLabel").pack(anchor=tk.W, pady=3)
        self.webhook_list = tk.Listbox(left_frame, font=("SimHei", 10))
        self.webhook_list.pack(fill=tk.BOTH, expand=True, pady=5)
        self.webhook_list.bind('<<ListboxSelect>>', self.on_webhook_select)
        ttk.Button(left_frame, text="添加 Webhook", command=self.add_webhook).pack(fill=tk.X, pady=3)
        ttk.Button(left_frame, text="编辑 Webhook", command=self.edit_webhook).pack(fill=tk.X, pady=3)
        ttk.Button(left_frame, text="删除 Webhook", command=self.delete_webhook).pack(fill=tk.X, pady=3)
        ttk.Button(left_frame, text="测试连接", command=self.test_webhook).pack(fill=tk.X, pady=3)

        # 右侧：主内容区 + 底部状态栏
        right_frame = ttk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---------- 主内容区（消息编辑、@用户、图片选择等） ----------
        main_content_frame = ttk.Frame(right_frame)
        main_content_frame.pack(fill=tk.BOTH, expand=True)

        # 当前Webhook状态
        self.webhook_status = ttk.Label(main_content_frame, text="请选择一个 Webhook", foreground="#86909c")
        self.webhook_status.pack(anchor=tk.W, pady=3)

        # 消息类型选择器
        msg_type_frame = ttk.Frame(main_content_frame)
        msg_type_frame.pack(fill=tk.X, pady=3)
        ttk.Label(msg_type_frame, text="消息类型:").pack(side=tk.LEFT)
        self.msg_type_combobox = ttk.Combobox(
            msg_type_frame,
            textvariable=self.msg_type_var,
            values=["Markdown", "图文消息(News)"],
            state="readonly"
        )
        self.msg_type_combobox.pack(side=tk.LEFT, padx=5)
        self.msg_type_combobox.bind("<<ComboboxSelected>>", self.on_msg_type_change)

        # Markdown输入区域
        self.markdown_frame = ttk.Frame(main_content_frame)
        ttk.Label(self.markdown_frame, text="Markdown 消息内容", style="Title.TLabel").pack(anchor=tk.W, pady=3)
        self.msg_text = tk.Text(self.markdown_frame, height=12, font=("SimHei", 10))
        self.msg_text.pack(fill=tk.BOTH, expand=True, pady=3)
        template_frame = ttk.Frame(self.markdown_frame)
        template_frame.pack(fill=tk.X, pady=3)
        ttk.Button(template_frame, text="加载模板", command=self.load_template).pack(side=tk.LEFT, padx=3)
        ttk.Button(template_frame, text="重置模板", command=self.reset_template).pack(side=tk.LEFT, padx=3)

        # 图文消息(News)输入区域
        self.news_frame = ttk.Frame(main_content_frame)
        ttk.Label(self.news_frame, text="图文消息内容（单条）", style="Title.TLabel").pack(anchor=tk.W, pady=3)

        # 1. 标题（必填）
        news_title_frame = ttk.Frame(self.news_frame)
        news_title_frame.pack(fill=tk.X, pady=2)
        ttk.Label(news_title_frame, text="*标题:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.news_title_entry = ttk.Entry(news_title_frame)
        self.news_title_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
        news_title_frame.columnconfigure(1, weight=1)

        # 2. 描述（可选）
        news_desc_frame = ttk.Frame(self.news_frame)
        news_desc_frame.pack(fill=tk.X, pady=2)
        ttk.Label(news_desc_frame, text="描述:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.news_desc_entry = ttk.Entry(news_desc_frame)
        self.news_desc_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
        news_desc_frame.columnconfigure(1, weight=1)

        # 3. 跳转链接（必填）
        news_url_frame = ttk.Frame(self.news_frame)
        news_url_frame.pack(fill=tk.X, pady=2)
        ttk.Label(news_url_frame, text="*跳转链接:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.news_url_entry = ttk.Entry(news_url_frame)
        self.news_url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
        news_url_frame.columnconfigure(1, weight=1)

        # 4. 图片链接（可选）
        news_picurl_frame = ttk.Frame(self.news_frame)
        news_picurl_frame.pack(fill=tk.X, pady=2)
        ttk.Label(news_picurl_frame, text="图片链接:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.news_picurl_entry = ttk.Entry(news_picurl_frame)
        self.news_picurl_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
        news_picurl_frame.columnconfigure(1, weight=1)

        # 图文消息提示
        ttk.Label(
            self.news_frame,
            text="注：*为必填项；图片建议尺寸：大图1068×455，小图150×150",
            foreground="#86909c",
            font=("SimHei", 9)
        ).pack(anchor=tk.W, pady=3)

        # @用户区域
        at_frame = ttk.Frame(main_content_frame)
        at_frame.pack(fill=tk.X, pady=3)
        ttk.Label(at_frame, text="@用户（手机号，多个用逗号分隔）:").pack(side=tk.LEFT)
        self.at_entry = ttk.Entry(at_frame)
        self.at_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        self.at_all_var = tk.BooleanVar()
        tk.Checkbutton(at_frame, text="@所有人", variable=self.at_all_var, font=("SimHei", 10)).pack(side=tk.LEFT)

        # 图片选择区域
        img_frame = ttk.Frame(main_content_frame)
        img_frame.pack(fill=tk.X, pady=3)
        self.img_label = ttk.Label(img_frame, text="未选择图片（可选，本地图片单独发送）", foreground="#86909c")
        self.img_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(img_frame, text="选择图片", command=self.select_image).pack(side=tk.LEFT, padx=3)
        ttk.Button(img_frame, text="清除图片", command=self.clear_image).pack(side=tk.LEFT, padx=3)

        # 图片预览区域
        self.img_preview = ttk.Label(main_content_frame, borderwidth=1, relief="solid")
        self.img_preview.pack(fill=tk.BOTH, expand=True, pady=5)

        # ---------- 底部状态栏（状态提示 + 发送按钮） ----------
        bottom_status_frame = ttk.Frame(right_frame)
        bottom_status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(bottom_status_frame, text="状态：就绪", foreground="#86909c")
        self.status_label.pack(side=tk.LEFT, padx=5, pady=3)
        self.send_btn = ttk.Button(bottom_status_frame, text="发送消息", command=self.send_message, state=tk.DISABLED)
        self.send_btn.pack(side=tk.RIGHT, padx=5, pady=3)

        # 初始化加载
        self.webhooks, load_status = self.load_webhooks_from_file()
        self.status_label.config(text=load_status, foreground="#008000")
        self.refresh_webhook_list()
        self.markdown_frame.pack(fill=tk.BOTH, expand=True, pady=3)  # 默认显示Markdown
        self.news_frame.pack_forget()  # 隐藏图文区域
        self.load_template()  # 加载默认模板

    def on_msg_type_change(self, event):
        """切换消息类型时，切换显示对应的输入区域"""
        current_type = self.msg_type_var.get()
        if current_type == "Markdown":
            self.markdown_frame.pack(fill=tk.BOTH, expand=True, pady=3)
            self.news_frame.pack_forget()
        elif current_type == "图文消息(News)":
            self.news_frame.pack(fill=tk.BOTH, expand=True, pady=3)
            self.markdown_frame.pack_forget()
        self.status_label.config(text="状态：就绪", foreground="#86909c")  # 重置状态提示

    # ---------- 核心：适配打包后的文件路径 ----------
    def get_real_path(self, filename):
        """处理打包后路径：开发时用脚本路径，打包后用exe所在路径"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller打包后，_MEIPASS为临时目录，取exe所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境，取当前脚本所在目录
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, filename)

    # ========== Webhook持久化：加载/保存（使用get_real_path） ==========
    def load_webhooks_from_file(self):
        config_file = self.get_real_path(CONFIG_FILENAME)
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data, f"状态：加载{len(data)}条Webhook记录"
                else:
                    messagebox.showwarning("数据错误", "配置文件格式异常，将重新创建")
                    return {}, "状态：配置文件异常，已重新创建"
            except Exception as e:
                messagebox.showerror("加载失败", f"读取配置出错：{str(e)}，将重新创建")
                return {}, f"状态：加载失败，已重新创建配置文件"
        else:
            # 首次运行，创建配置文件
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}, "状态：首次运行，创建配置文件"

    def save_webhooks_to_file(self):
        config_file = self.get_real_path(CONFIG_FILENAME)
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.webhooks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("保存失败", f"写入配置出错：{str(e)}")
            return False

    # ========== Webhook操作：添加/编辑/删除 ==========
    def add_webhook(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("添加 Webhook")
        dialog.geometry("600x280")
        dialog.resizable(True, True)
        self.center_dialog(dialog)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Webhook名称:").grid(row=0, column=0, sticky=tk.W, pady=8)
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=8, ipady=3)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Webhook地址:").grid(row=1, column=0, sticky=tk.W, pady=8)
        url_entry = ttk.Entry(frame)
        url_entry.grid(row=1, column=1, sticky=tk.EW, pady=8, ipady=3)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=tk.E)
        ttk.Button(
            btn_frame,
            text="确定",
            command=lambda: self.save_webhook(dialog, name_entry.get(), url_entry.get())
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)
        name_entry.focus_set()

    def save_webhook(self, dialog, name, url):
        if not (name and url):
            messagebox.showwarning("输入错误", "名称和Webhook地址不能为空！")
            return
        if name in self.webhooks:
            messagebox.showwarning("重复错误", f"已存在名为「{name}」的Webhook！")
            return
        self.webhooks[name] = url
        self.webhook_list.insert(tk.END, name)
        self.save_webhooks_to_file()
        dialog.destroy()
        messagebox.showinfo("添加成功", f"Webhook「{name}」已保存")

    def edit_webhook(self):
        if not self.current_webhook:
            messagebox.showinfo("提示", "请先选择一个Webhook")
            return
        current_url = self.webhooks.get(self.current_webhook, "")
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑 Webhook")
        dialog.geometry("600x260")
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
        url_entry.grid(row=1, column=1, sticky=tk.EW, padx=8, ipady=3)
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

    def update_webhook(self, dialog, new_url):
        if not new_url:
            messagebox.showwarning("输入错误", "Webhook地址不能为空！")
            return
        self.webhooks[self.current_webhook] = new_url
        if self.save_webhooks_to_file():
            dialog.destroy()
            self.status_label.config(text="状态：Webhook已更新", foreground="#008000")
            messagebox.showinfo("更新成功", f"Webhook「{self.current_webhook}」地址已更新")

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

    # ========== 测试Webhook连接 ==========
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

    # ========== 图片选择与预览 ==========
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

    # ========== 发送消息（Markdown/图文双类型） ==========
    def send_message(self):
        if not self.current_webhook:
            messagebox.showinfo("提示", "请先选择一个Webhook")
            return

        current_msg_type = self.msg_type_var.get()
        mentioned_mobiles = []
        main_msg_data = None

        # 处理@用户逻辑
        if self.at_all_var.get():
            mentioned_mobiles.append("all")
        at_users = self.at_entry.get().strip().split(",") if self.at_entry.get().strip() else []
        for phone in at_users:
            phone = phone.strip()
            if phone and phone != "all":
                mentioned_mobiles.append(phone)

        # 构造消息数据
        if current_msg_type == "Markdown":
            msg_content = self.msg_text.get("1.0", tk.END).strip()
            if not msg_content:
                messagebox.showwarning("内容为空", "请输入Markdown消息内容")
                return
            if self.at_all_var.get():
                msg_content += "\n<@all>"
            for phone in at_users:
                phone = phone.strip()
                if phone and phone != "all":
                    msg_content += f"\n<@{phone}>"
            main_msg_data = {
                "msgtype": "markdown",
                "markdown": {"content": msg_content},
                "mentioned_mobile_list": mentioned_mobiles
            }

        elif current_msg_type == "图文消息(News)":
            news_title = self.news_title_entry.get().strip()
            news_desc = self.news_desc_entry.get().strip()
            news_url = self.news_url_entry.get().strip()
            news_picurl = self.news_picurl_entry.get().strip()

            if not news_title:
                messagebox.showwarning("输入错误", "请填写图文消息【标题】（必填）")
                return
            if not news_url:
                messagebox.showwarning("输入错误", "请填写图文消息【跳转链接】（必填）")
                return

            if len(news_title.encode("utf-8")) > 128:
                messagebox.showwarning("长度超限", "标题不能超过128字节（约42个中文字符）")
                return
            if news_desc and len(news_desc.encode("utf-8")) > 512:
                messagebox.showwarning("长度超限", "描述不能超过512字节（约170个中文字符）")
                return

            article = {"title": news_title, "url": news_url}
            if news_desc:
                article["description"] = news_desc
            if news_picurl:
                article["picurl"] = news_picurl
            main_msg_data = {
                "msgtype": "news",
                "news": {"articles": [article]},
                "mentioned_mobile_list": mentioned_mobiles
            }

        # 发送消息（多线程避免UI卡死）
        webhook_url = self.webhooks[self.current_webhook]
        self.send_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"状态：正在发送{current_msg_type}消息...", foreground="#ff8c00")
        self.root.update()

        def send():
            try:
                # 发送主消息
                main_response = requests.post(webhook_url, json=main_msg_data, timeout=10)
                main_response.raise_for_status()
                main_result = main_response.json()
                if main_result.get("errcode") != 0:
                    raise Exception(f"{current_msg_type}发送失败：{main_result.get('errmsg')}")

                # 发送附加图片
                img_sent = False
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
                        raise Exception(f"附加图片发送失败：{img_result.get('errmsg')}")
                    img_sent = True

                success_msg = f"{current_msg_type}消息已发送"
                if img_sent:
                    success_msg += "和附加图片"
                self.status_label.config(text="状态：消息发送成功", foreground="#008000")
                messagebox.showinfo("发送成功", success_msg)

            except Exception as e:
                self.status_label.config(text=f"状态：发送失败 - {str(e)}", foreground="#ff0000")
                messagebox.showerror("发送失败", f"错误原因：{str(e)}")

            finally:
                self.send_btn.config(state=tk.NORMAL)

        threading.Thread(target=send, daemon=True).start()

    # ========== Markdown模板 ==========
    def load_template(self):
        self.msg_text.delete("1.0", tk.END)
        self.msg_text.insert("1.0", self.DEFAULT_MARKDOWN_TEMPLATE)
        self.status_label.config(text="状态：模板已加载", foreground="#008000")

    def reset_template(self):
        if messagebox.askyesno("确认重置", "确定要恢复默认模板吗？当前内容将被覆盖"):
            self.load_template()

    # ========== UI辅助：Webhook选择、窗口居中 ==========
    def on_webhook_select(self, event):
        selection = self.webhook_list.curselection()
        if selection:
            self.current_webhook = self.webhook_list.get(selection[0])
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