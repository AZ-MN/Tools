import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import base64
import hashlib
import threading
import json
import os
import sys
import io

# 配置文件名（持久化Webhook）
CONFIG_FILENAME = "webhooks_config.json"


class WeChatRobotSender:
    def __init__(self, root):
        self.root = root
        self.root.title("企微消息推送")
        self.root.geometry("1000x800")
        self.root.minsize(1000, 800)  # 设置窗口最小尺寸

        # 全局样式配置 - 简洁外观
        self.style = ttk.Style()
        # 全局字体
        self.style.configure(".", font=("SimHei", 10))
        # 标题样式
        self.style.configure("Title.TLabel", font=("SimHei", 11, "bold"))
        # 按钮样式
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.map("TButton", 
            foreground=[("pressed", "#000000"), ("active", "#0066cc")]
        )
        # 输入框样式
        self.style.configure("TEntry", padding=3)
        # 组合框样式
        self.style.configure("TCombobox", padding=3)

        # 初始化数据
        self.webhooks = {}
        self.current_webhook = None
        self.image_path = None
        self.msg_type_var = tk.StringVar(value="Markdown")  # 默认消息类型
        
        # 图文卡片消息字段
        self.template_card_fields = {
            'main_title': '',
            'main_desc': '',
            'vertical_contents': [],
            'horizontal_contents': [],
            'jump_links': []
        }

        # Markdown默认模板
        self.DEFAULT_MARKDOWN_TEMPLATE = """
# 企微消息 Markdown 格式示范
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

        # Markdown V2默认模板
        self.DEFAULT_MARKDOWN_V2_TEMPLATE = """
# 一、标题
## 二级标题
### 三级标题
# 二、字体
*斜体*
**加粗**
# 三、列表
- 无序列表 1
- 无序列表 2
1. 有序列表 1
2. 有序列表 2
# 四、引用
> 一级引用
>>二级引用

# 五、链接
[这是一个链接](https://work.weixin.qq.com/api)
[图片](https://res.mail.qq.com/node/wx_moppening/images/independent/doc/test_pic_msg1.png)
# 六、分割线

---

# 七、代码
`这是行内代码`
```\n这是独立代码块\n```
        """

        # ========== UI组件创建 ==========
        # 左侧：Webhook列表与操作（优化布局和间距）
        left_frame = ttk.Frame(root, width=240)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        ttk.Label(left_frame, text="Webhook 列表", style="Title.TLabel").pack(anchor=tk.W, pady=5)
        # 简洁的Listbox
        self.webhook_list = tk.Listbox(left_frame, font=("SimHei", 12))
        self.webhook_list.pack(fill=tk.BOTH, expand=True, pady=5)
        self.webhook_list.bind('<<ListboxSelect>>', self.on_webhook_select)
        # 按钮间距调整
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="添加 Webhook", command=self.add_webhook).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="编辑 Webhook", command=self.edit_webhook).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="删除 Webhook", command=self.delete_webhook).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="测试连接", command=self.test_webhook).pack(fill=tk.X, pady=2)

        # 右侧：主内容区 + 底部状态栏（优化布局和间距）
        right_frame = ttk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ---------- 主内容区（消息编辑、@用户、图片选择等） ----------
        main_content_frame = ttk.Frame(right_frame)
        main_content_frame.pack(fill=tk.BOTH, expand=True)

        # 当前Webhook状态
        self.webhook_status = ttk.Label(main_content_frame, text="请选择一个 Webhook", font=("SimHei", 10, "bold"), foreground="#86909c")
        self.webhook_status.pack(anchor=tk.W, pady=5)

        # 消息类型选择器（优化外观）
        msg_type_frame = ttk.Frame(main_content_frame)
        msg_type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(msg_type_frame, text="消息类型:", width=10).pack(side=tk.LEFT)
        self.msg_type_combobox = ttk.Combobox(
            msg_type_frame,
            textvariable=self.msg_type_var,
            values=["Markdown", "Markdown V2", "图文消息(News)", "图文卡片消息(TemplateCard)"],
            state="readonly",
            width=30
        )
        self.msg_type_combobox.pack(side=tk.LEFT, padx=5)
        self.msg_type_combobox.bind("<<ComboboxSelected>>", self.on_msg_type_change)

        # Markdown输入区域（优化外观和功能）
        self.markdown_frame = ttk.Frame(main_content_frame)
        # 根据消息类型显示不同的标题
        self.markdown_title = ttk.Label(self.markdown_frame, text="Markdown 消息内容", style="Title.TLabel")
        self.markdown_title.pack(anchor=tk.W, pady=5)
        # 简洁的文本框
        self.msg_text = tk.Text(self.markdown_frame, height=12, font=('SimHei', 10), wrap=tk.WORD)
        self.msg_text.pack(fill=tk.BOTH, expand=True, pady=5)
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.msg_text, command=self.msg_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.msg_text.config(yscrollcommand=scrollbar.set)
        # 模板按钮
        template_frame = ttk.Frame(self.markdown_frame)
        template_frame.pack(fill=tk.X, pady=5)
        ttk.Button(template_frame, text="加载模板", command=self.load_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(template_frame, text="重置模板", command=self.reset_template).pack(side=tk.LEFT, padx=5)
        
        # 图文卡片消息(TemplateCard)输入区域 - 重构为独立输入框
        self.template_card_frame = ttk.Frame(main_content_frame)
        ttk.Label(self.template_card_frame, text="图文卡片消息内容", style="Title.TLabel").pack(anchor=tk.W, pady=5)
        
        # 主标题信息
        main_title_frame = ttk.LabelFrame(self.template_card_frame, text="主标题信息（必填）")
        main_title_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # 主标题
        title_frame = ttk.Frame(main_title_frame)
        title_frame.pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(title_frame, text="*主标题:", width=15).pack(side=tk.LEFT)
        self.main_title_entry = ttk.Entry(title_frame)
        self.main_title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 主标题描述
        main_desc_frame = ttk.Frame(main_title_frame)
        main_desc_frame.pack(fill=tk.X, pady=2, padx=10)
        ttk.Label(main_desc_frame, text="主标题描述:", width=15).pack(side=tk.LEFT)
        self.main_desc_entry = ttk.Entry(main_desc_frame)
        self.main_desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 垂直内容列表
        self.vertical_contents_frame = ttk.LabelFrame(self.template_card_frame, text="垂直内容列表（选填，可定义多条）")
        self.vertical_contents_frame.pack(fill=tk.X, pady=5, padx=5)
        self.vertical_entries = []
        add_vertical_btn = ttk.Button(self.vertical_contents_frame, text="添加垂直内容", command=self.add_vertical_content)
        add_vertical_btn.pack(anchor=tk.W, pady=5, padx=10)
        
        # 水平内容列表
        self.horizontal_contents_frame = ttk.LabelFrame(self.template_card_frame, text="水平内容列表（选填，可定义多条）")
        self.horizontal_contents_frame.pack(fill=tk.X, pady=5, padx=5)
        self.horizontal_entries = []
        add_horizontal_btn = ttk.Button(self.horizontal_contents_frame, text="添加水平内容", command=self.add_horizontal_content)
        add_horizontal_btn.pack(anchor=tk.W, pady=5, padx=10)
        
        # 跳转链接列表
        self.jump_links_frame = ttk.LabelFrame(self.template_card_frame, text="跳转链接列表（选填，可定义多条）")
        self.jump_links_frame.pack(fill=tk.X, pady=5, padx=5)
        self.jump_entries = []
        add_jump_btn = ttk.Button(self.jump_links_frame, text="添加跳转链接", command=self.add_jump_link)
        add_jump_btn.pack(anchor=tk.W, pady=5, padx=10)
        
        # 提示信息
        ttk.Label(
            self.template_card_frame,
            text="注：*为必填项；图片通过上方选择本地/网络图片自动处理",
            foreground="#86909c",
            font=("SimHei", 9)
        ).pack(anchor=tk.W, pady=5, padx=5)

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

        # 图片选择区域（仅保留基本功能，移除预览相关元素）
        img_frame = ttk.Frame(main_content_frame)
        img_frame.pack(fill=tk.X, pady=5)
        self.img_label = ttk.Label(img_frame, text="未选择图片（可选）", foreground="#86909c")
        self.img_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(img_frame, text="选择本地图片", command=self.select_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(img_frame, text="清除图片", command=self.clear_image).pack(side=tk.LEFT, padx=5)
        
        # 图片发送方式选择区域
        img_send_type_frame = ttk.Frame(main_content_frame)
        img_send_type_frame.pack(fill=tk.X, pady=2, padx=5)
        ttk.Label(img_send_type_frame, text="图片发送方式:", width=15).pack(side=tk.LEFT)
        self.img_send_type = tk.StringVar(value="图床转URL")
        send_type_frame = ttk.Frame(img_send_type_frame)
        send_type_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Radiobutton(send_type_frame, text="图床转URL", variable=self.img_send_type, value="图床转URL").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(send_type_frame, text="直接发送", variable=self.img_send_type, value="直接发送").pack(side=tk.LEFT, padx=5)
        
        # 网络图片URL输入区域
        net_img_frame = ttk.Frame(main_content_frame)
        net_img_frame.pack(fill=tk.X, pady=2)
        ttk.Label(net_img_frame, text="网络图片URL:", width=15).pack(side=tk.LEFT, padx=5)
        self.net_img_url_entry = ttk.Entry(net_img_frame)
        self.net_img_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(net_img_frame, text="使用网络图片", command=self.load_net_image).pack(side=tk.LEFT, padx=5)

        # ---------- 底部状态栏（状态提示 + 发送按钮） ----------
        bottom_status_frame = ttk.Frame(right_frame, height=40)
        bottom_status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        bottom_status_frame.pack_propagate(False)  # 防止框架缩小

        self.status_label = ttk.Label(bottom_status_frame, text="状态：就绪", foreground="#666666")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=8)
        # 美化发送按钮
        self.send_btn = ttk.Button(bottom_status_frame, text="发送消息", command=self.send_message, state=tk.DISABLED, width=15)
        self.send_btn.pack(side=tk.RIGHT, padx=10, pady=8)

        # 初始化加载
        self.webhooks, load_status = self.load_webhooks_from_file()
        self.status_label.config(text=load_status, foreground="#008000")
        self.refresh_webhook_list()
        self.markdown_frame.pack(fill=tk.BOTH, expand=True, pady=3)  # 默认显示Markdown
        self.news_frame.pack_forget()  # 隐藏图文区域
        self.template_card_frame.pack_forget()  # 隐藏图文卡片区域
        self.load_template()  # 加载默认模板

    def on_msg_type_change(self, event):
        """切换消息类型时，切换显示对应的输入区域"""
        current_type = self.msg_type_var.get()
        # 隐藏所有框架
        self.markdown_frame.pack_forget()
        self.news_frame.pack_forget()
        self.template_card_frame.pack_forget()
        
        if current_type == "Markdown" or current_type == "Markdown V2":
            self.markdown_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            # 更新Markdown区域标题
            if current_type == "Markdown":
                self.markdown_title.config(text="Markdown 消息内容")
                self.msg_text.delete("1.0", tk.END)
                self.msg_text.insert("1.0", self.DEFAULT_MARKDOWN_TEMPLATE)
            elif current_type == "Markdown V2":
                self.markdown_title.config(text="Markdown V2 消息内容")
                self.msg_text.delete("1.0", tk.END)
                self.msg_text.insert("1.0", self.DEFAULT_MARKDOWN_V2_TEMPLATE)
        elif current_type == "图文消息(News)":
            self.news_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        elif current_type == "图文卡片消息(TemplateCard)":
            self.template_card_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            # 图片现在是可选的，不做强制要求
            if not self.image_path and not self.net_img_url_entry.get().strip():
                self.status_label.config(text="状态：将发送不含图片的卡片消息", foreground="#ff8c00")

    # ========== Markdown模板 ==========
    def load_template(self):
        current_type = self.msg_type_var.get()
        if current_type == "Markdown":
            self.msg_text.delete("1.0", tk.END)
            self.msg_text.insert("1.0", self.DEFAULT_MARKDOWN_TEMPLATE)
        elif current_type == "Markdown V2":
            self.msg_text.delete("1.0", tk.END)
            self.msg_text.insert("1.0", self.DEFAULT_MARKDOWN_V2_TEMPLATE)
        elif current_type == "图文卡片消息(TemplateCard)":
            self.msg_text.delete("1.0", tk.END)
            self.msg_text.insert("1.0", self.DEFAULT_TEMPLATE_CARD_TEMPLATE)
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
                                       font=("SimHei", 14, "bold"))
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

    # ========== 图文卡片消息内容管理方法 ==========
    def add_vertical_content(self):
        """添加垂直内容条目"""
        frame = ttk.Frame(self.vertical_contents_frame)
        frame.pack(fill=tk.X, pady=2, padx=10)
        
        title_label = ttk.Label(frame, text="标题:", width=15)
        title_label.pack(side=tk.LEFT)
        title_entry = ttk.Entry(frame)
        title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        desc_label = ttk.Label(frame, text="描述:", width=15)
        desc_label.pack(side=tk.LEFT)
        desc_entry = ttk.Entry(frame)
        desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 删除按钮
        remove_btn = ttk.Button(frame, text="删除", command=lambda: self.remove_vertical_content(frame, title_entry, desc_entry))
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # 保存引用
        self.vertical_entries.append((frame, title_entry, desc_entry))
        
    def remove_vertical_content(self, frame, title_entry, desc_entry):
        """删除垂直内容条目"""
        # 从列表中移除引用
        for i, (f, te, de) in enumerate(self.vertical_entries):
            if f == frame and te == title_entry and de == desc_entry:
                self.vertical_entries.pop(i)
                break
        # 销毁框架
        frame.destroy()
    
    def add_horizontal_content(self):
        """添加水平内容条目"""
        frame = ttk.Frame(self.horizontal_contents_frame)
        frame.pack(fill=tk.X, pady=2, padx=10)
        
        key_label = ttk.Label(frame, text="键名:", width=15)
        key_label.pack(side=tk.LEFT)
        key_entry = ttk.Entry(frame)
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        value_label = ttk.Label(frame, text="值:", width=15)
        value_label.pack(side=tk.LEFT)
        value_entry = ttk.Entry(frame)
        value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 删除按钮
        remove_btn = ttk.Button(frame, text="删除", command=lambda: self.remove_horizontal_content(frame, key_entry, value_entry))
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # 保存引用
        self.horizontal_entries.append((frame, key_entry, value_entry))
        
    def remove_horizontal_content(self, frame, key_entry, value_entry):
        """删除水平内容条目"""
        # 从列表中移除引用
        for i, (f, ke, ve) in enumerate(self.horizontal_entries):
            if f == frame and ke == key_entry and ve == value_entry:
                self.horizontal_entries.pop(i)
                break
        # 销毁框架
        frame.destroy()
    
    def add_jump_link(self):
        """添加跳转链接条目 - 优化布局"""
        # 创建主框架
        frame = ttk.Frame(self.jump_links_frame)
        frame.pack(fill=tk.X, pady=2, padx=10)
        
        # 第一行：类型选择
        type_frame = ttk.Frame(frame)
        type_frame.pack(fill=tk.X, pady=2)
        
        type_label = ttk.Label(type_frame, text="类型:", width=15)
        type_label.pack(side=tk.LEFT)
        type_var = tk.IntVar(value=1)  # 默认为跳转URL
        
        radio_frame = ttk.Frame(type_frame)
        radio_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Radiobutton(radio_frame, text="跳转URL", variable=type_var, value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(radio_frame, text="跳转小程序", variable=type_var, value=2).pack(side=tk.LEFT, padx=5)
        
        # 第二行：URL和标题输入框
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=tk.X, pady=2)
        
        url_label = ttk.Label(input_frame, text="URL:", width=15)
        url_label.pack(side=tk.LEFT)
        url_entry = ttk.Entry(input_frame)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        title_label = ttk.Label(input_frame, text="标题:", width=15)
        title_label.pack(side=tk.LEFT)
        title_entry = ttk.Entry(input_frame)
        title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 删除按钮
        remove_btn = ttk.Button(input_frame, text="删除", command=lambda: self.remove_jump_link(frame, type_var, url_entry, title_entry))
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # 保存引用
        self.jump_entries.append((frame, type_var, url_entry, title_entry))
        
    def remove_jump_link(self, frame, type_var, url_entry, title_entry):
        """删除跳转链接条目"""
        # 从列表中移除引用
        for i, (f, tv, ue, te) in enumerate(self.jump_entries):
            if f == frame and tv == type_var and ue == url_entry and te == title_entry:
                self.jump_entries.pop(i)
                break
        # 销毁框架
        frame.destroy()
    
    # ========== 图片选择与处理方法 ==========
    def select_image(self):
        """选择本地图片"""
        file_types = [
            ("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"),
            ("所有文件", "*.*")
        ]
        
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(title="选择图片文件", filetypes=file_types)
        
        if file_path:
            try:
                # 保存图片路径
                self.image_path = file_path
                # 清除网络图片URL
                self.net_img_url_entry.delete(0, tk.END)
                
                # 显示文件名
                file_name = os.path.basename(file_path)
                self.img_label.config(text=f"已选择本地图片：{file_name}", foreground="#008000")
                
                # 更新状态
                self.status_label.config(text="状态：图片已选择", foreground="#008000")
                
            except Exception as e:
                self.status_label.config(text=f"状态：图片选择失败 - {str(e)}", foreground="#ff0000")
                messagebox.showerror("图片选择失败", f"错误原因：{str(e)}")
                self.clear_image()
                
    def load_net_image(self):
        """使用网络图片"""
        net_img_url = self.net_img_url_entry.get().strip()
        if not net_img_url:
            messagebox.showwarning("输入错误", "请输入网络图片URL")
            return
        
        try:
            # 清除本地图片选择
            self.image_path = None
            
            # 显示URL状态
            self.img_label.config(text=f"已选择网络图片", foreground="#008000")
            
            # 验证URL是否有效
            response = requests.head(net_img_url, timeout=10)
            response.raise_for_status()
            
            # 更新状态
            self.status_label.config(text="状态：网络图片已设置", foreground="#008000")
            
        except Exception as e:
            self.status_label.config(text=f"状态：网络图片设置失败 - {str(e)}", foreground="#ff0000")
            messagebox.showerror("网络图片设置失败", f"错误原因：{str(e)}")
    
    def clear_image(self):
        """清除已选择的图片"""
        self.image_path = None
        self.net_img_url_entry.delete(0, tk.END)
        self.img_label.config(text="未选择图片（可选）", foreground="#86909c")
        self.status_label.config(text="状态：图片已清除", foreground="#008000")

    def upload_image_to_free_host(self):
        """将本地图片上传到免费图床服务，获取公网可访问的URL
        注意：这个方法使用免费图床服务，可能有使用限制和隐私风险"""
        if not self.image_path or not os.path.exists(self.image_path):
            raise Exception("没有选择有效的本地图片")

        try:
            # 读取图片文件
            with open(self.image_path, "rb") as f:
                img_data = f.read()
                img_size = len(img_data) / 1024 / 1024  # 转换为MB
                
            # 检查文件大小是否超过限制
            # 根据imgbed.cn的信息，最大支持100MB
            if img_size > 100:
                raise Exception(f"图片大小超过限制 (当前: {img_size:.2f}MB, 限制: 100MB)")
                
            # 状态更新
            self.status_label.config(text="状态：正在上传图片到免费图床...", foreground="#ff8c00")
            self.root.update()
            
            # 使用用户提供的imgbed.cn图床服务的正确接口
            url = "https://imgbed.cn/img/upload"

            # 使用用户提供的Java示例中的正确上传接口
            # url = "https://playground.z.wiki/img/api/upload"
            
            # 准备上传文件
            # 添加MIME类型以解决'未识别到文件类型'的问题
            import mimetypes
            mime_type, _ = mimetypes.guess_type(self.image_path)
            if not mime_type:
                # 如果无法识别MIME类型，默认为二进制流
                mime_type = 'application/octet-stream'
            
            files = {
                'file': (os.path.basename(self.image_path), img_data, mime_type)
            }
            
            # 添加表单数据（根据用户提供的Java示例）
            data = {
                'fileName': os.path.basename(self.image_path),
                'uid': '3dfd757677824cecadcd7640baeb787d',  # 使用用户提供的示例UID/token
            }
            
            # 添加请求头
            headers = {
                'accept': 'application/json, text/plain, */*',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
            }
            
            # 发送请求
            response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
            
            # 打印完整响应信息（调试用）
            print(f"======= 图床接口响应信息 =======")
            print(f"请求URL: {url}")
            print(f"请求参数: {data}")
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            print(f"响应内容: {response.text}")
            print(f"==============================\n")
            
            # 检查响应状态
            if response.status_code == 200:
                # 尝试解析JSON响应（根据API接口）
                try:
                    result = response.json()
                    # 检查是否有错误信息
                    if result.get('error'):
                        raise Exception(f"图片上传失败: {result.get('error')}")
                    
                    # 从实际响应中提取URL（根据打印的响应内容分析）
                    # 响应格式是 {"url":"...", "id":"...", ...} 而不是嵌套的data列表
                    if result.get('url'):
                        image_url = result.get('url')
                        if image_url:
                            self.status_label.config(text="状态：图片上传成功", foreground="#008000")
                            self.root.update()
                            return image_url
                        else:
                            raise Exception("图片上传成功但未获取到图片URL")
                    else:
                        raise Exception(f"图片上传响应格式异常: {result}")
                except ValueError:
                    # 如果响应不是JSON格式，尝试使用正则表达式提取URL
                    import re
                    match = re.search(r'https://[^"\']+', response.text)
                    if match:
                        image_url = match.group(0)
                        self.status_label.config(text="状态：图片上传成功", foreground="#008000")
                        self.root.update()
                        return image_url
                
                raise Exception("无法从响应中提取图片URL，请检查图床服务是否正常")
            else:
                raise Exception(f"图片上传失败，HTTP状态码: {response.status_code}\n响应内容: {response.text}")
                       
        except ImportError:
            # 如果没有安装BeautifulSoup，提供更简单的解析方式
            # 尝试使用正则表达式提取URL
            import re
            match = re.search(r'https://[^"\']+', response.text)
            if match:
                image_url = match.group(0)
                self.status_label.config(text="状态：图片上传成功", foreground="#008000")
                self.root.update()
                return image_url
            else:
                raise Exception("无法从响应中提取图片URL，建议安装BeautifulSoup库")
        
        except Exception as e:
            error_msg = str(e)
            self.status_label.config(text=f"状态：图片上传失败 - {error_msg}", foreground="#ff0000")
            self.root.update()
            raise Exception(f"上传图片失败: {error_msg}\n\n建议解决方法：\n1. 尝试使用网络图片URL代替本地图片\n2. 检查网络连接是否正常\n3. 考虑使用其他图床服务")
    
    def send_message(self):
        """发送消息，支持不同类型的消息"""
        if not self.current_webhook:
            messagebox.showinfo("提示", "请先选择一个Webhook")
            return

        current_type = self.msg_type_var.get()
        webhook_url = self.webhooks[self.current_webhook]
        self.send_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态：正在发送消息...", foreground="#ff8c00")
        self.root.update()

        def send():
            try:
                if current_type == "Markdown" or current_type == "Markdown V2":
                    msg_content = self.msg_text.get("1.0", tk.END).strip()
                    if not msg_content:
                        raise Exception("请输入Markdown消息内容")

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

                    # 发送Markdown
                    # 处理本地图片或网络图片
                    image_url = ""
                    if self.net_img_url_entry.get().strip():
                        # 使用已有的网络图片URL
                        image_url = self.net_img_url_entry.get().strip()
                    elif self.image_path:
                        # 根据选择的方式处理图片
                        if self.img_send_type.get() == "图床转URL":
                            # 上传本地图片到免费图床
                            try:
                                image_url = self.upload_image_to_free_host()
                            except Exception as e:
                                messagebox.showerror("图片上传失败", f"无法上传图片到图床：{str(e)}")
                                # 即使图片上传失败，也继续发送Markdown消息
                        else:  # 直接发送
                            # Markdown不支持直接发送本地图片，只能使用图床转URL
                            messagebox.showinfo("提示", "Markdown消息不支持直接发送本地图片，请选择'图床转URL'方式")
                            try:
                                image_url = self.upload_image_to_free_host()
                            except Exception as e:
                                messagebox.showerror("图片上传失败", f"无法上传图片到图床：{str(e)}")
                    
                    # 如果有图片，添加到Markdown内容中
                    if image_url:
                        # 在Markdown内容末尾添加图片
                        msg_content += f"\n![图片]({image_url})"
                    
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

                    self.status_label.config(text="状态：消息发送成功", foreground="#008000")
                    msg = "Markdown消息已发送"
                    messagebox.showinfo("发送成功", msg)

                elif current_type == "图文消息(News)":
                    news_title = self.news_title_entry.get().strip()
                    news_desc = self.news_desc_entry.get().strip()
                    news_url = self.news_url_entry.get().strip()
                    news_picurl = self.news_picurl_entry.get().strip()
                    
                    # 检查是否有选择本地图片或网络图片
                    if not news_picurl:
                        if self.net_img_url_entry.get().strip():
                            # 使用已有的网络图片URL
                            news_picurl = self.net_img_url_entry.get().strip()
                        elif self.image_path:
                            # 根据选择的方式处理图片
                            if self.img_send_type.get() == "图床转URL":
                                # 上传本地图片到免费图床
                                try:
                                    news_picurl = self.upload_image_to_free_host()
                                except Exception as e:
                                    messagebox.showerror("图片上传失败", f"无法上传图片到图床：{str(e)}")
                                    # 即使图片上传失败，也继续发送消息（图片为可选）
                            else:  # 直接发送
                                # 对于图文消息(News)类型，不支持直接发送本地图片，只能使用URL
                                messagebox.showinfo("提示", "图文消息(News)不支持直接发送本地图片，请选择'图床转URL'方式")
                                try:
                                    news_picurl = self.upload_image_to_free_host()
                                except Exception as e:
                                    messagebox.showerror("图片上传失败", f"无法上传图片到图床：{str(e)}")

                    if not news_title:
                        raise Exception("请填写图文消息【标题】（必填）")
                    if not news_url:
                        raise Exception("请填写图文消息【跳转链接】（必填）")

                    if len(news_title.encode("utf-8")) > 128:
                        raise Exception("标题不能超过128字节（约42个中文字符）")
                    if news_desc and len(news_desc.encode("utf-8")) > 512:
                        raise Exception("描述不能超过512字节（约170个中文字符）")

                    # 构造图文消息数据
                    news_data = {
                        "msgtype": "news",
                        "news": {
                            "articles": [{
                                "title": news_title,
                                "description": news_desc,
                                "url": news_url
                            }]
                        }
                    }
                    
                    if news_picurl:
                        news_data["news"]["articles"][0]["picurl"] = news_picurl
                    
                    # 发送图文消息
                    response = requests.post(webhook_url, json=news_data, timeout=10)
                    response.raise_for_status()
                    result = response.json()
                    if result.get("errcode") != 0:
                        raise Exception(f"图文消息发送失败：{result.get('errmsg')}（错误码：{result.get('errcode')}）")

                    self.status_label.config(text="状态：图文消息发送成功", foreground="#008000")
                    messagebox.showinfo("发送成功", "图文消息已发送")

                elif current_type == "图文卡片消息(TemplateCard)":
                    # 验证必填字段
                    main_title = self.main_title_entry.get().strip()
                    if not main_title:
                        raise Exception("图文卡片消息的【主标题】为必填项，请填写！")

                    # 构造图文卡片消息数据 - 根据模板JSON格式
                    template_data = {
                        "msgtype": "template_card",
                        "template_card": {
                            "card_type": "news_notice",
                            "main_title": {
                                "title": main_title
                            },
                            "vertical_content_list": [],
                            "horizontal_content_list": [],
                            "jump_list": [],
                            "card_action": {}
                        }
                    }

                    # 填充主标题描述（如果有）
                    main_desc = self.main_desc_entry.get().strip()
                    if main_desc:
                        template_data["template_card"]["main_title"]["desc"] = main_desc

                    # 处理图片：将本地图片上传到免费图床获取公网URL
                    image_url = ""
                    if self.net_img_url_entry.get().strip():
                        # 使用已有的网络图片URL
                        image_url = self.net_img_url_entry.get().strip()
                    elif self.image_path:
                        # 根据选择的方式处理图片
                        if self.img_send_type.get() == "图床转URL":
                            # 上传本地图片到免费图床
                            try:
                                image_url = self.upload_image_to_free_host()
                            except Exception as e:
                                messagebox.showerror("图片上传失败", f"无法上传图片到图床：{str(e)}")
                        else:  # 直接发送
                            # 对于图文卡片消息，也需要先上传到图床
                            messagebox.showinfo("提示", "图文卡片消息不支持直接发送本地图片，请选择'图床转URL'方式")
                            try:
                                image_url = self.upload_image_to_free_host()
                            except Exception as e:
                                messagebox.showerror("图片上传失败", f"无法上传图片到图床：{str(e)}")
                            
                    # 只有当有有效URL时才添加图片相关字段，避免出现默认机器人图标
                    if image_url:
                        template_data["template_card"]["card_image"] = {
                            "url": image_url,
                            "aspect_ratio": 2.25  # 标准宽高比
                        }
                        # 不添加image_text_area字段，避免出现小图片
                        # template_data["template_card"]["image_text_area"] = {
                        #     "image_url": image_url
                        # }

                    # 填充垂直内容列表
                    vertical_content_list = []
                    for frame, title_entry, desc_entry in self.vertical_entries:
                        title = title_entry.get().strip()
                        desc = desc_entry.get().strip()
                        if title or desc:
                            item = {}
                            if title:
                                item["title"] = title
                            if desc:
                                item["desc"] = desc
                            vertical_content_list.append(item)
                    if vertical_content_list:
                        template_data["template_card"]["vertical_content_list"] = vertical_content_list

                    # 填充水平内容列表
                    horizontal_content_list = []
                    for frame, key_entry, value_entry in self.horizontal_entries:
                        keyname = key_entry.get().strip()
                        value = value_entry.get().strip()
                        if keyname and value:
                            horizontal_content_list.append({
                                "keyname": keyname,
                                "value": value
                            })
                    if horizontal_content_list:
                        template_data["template_card"]["horizontal_content_list"] = horizontal_content_list

                    # 填充跳转链接列表和卡片点击行为
                    jump_list = []
                    card_action = {}
                    card_action_set = False
                    for frame, type_var, url_entry, title_entry in self.jump_entries:
                        jump_type = type_var.get()
                        jump_url = url_entry.get().strip()
                        jump_title = title_entry.get().strip()
                        
                        if jump_url and jump_title:
                            # 添加到跳转列表
                            jump_list.append({
                                "type": jump_type,
                                "url": jump_url,
                                "title": jump_title
                            })
                            
                            # 设置card_action（卡片点击行为），使用第一个有效的跳转链接
                            if not card_action_set:
                                card_action = {
                                    "type": jump_type,
                                    "url": jump_url,
                                    "title": jump_title
                                }
                                card_action_set = True
                    
                    # 更新跳转列表
                    if jump_list:
                        template_data["template_card"]["jump_list"] = jump_list
                    
                    # 设置卡片点击行为
                    if card_action:
                        template_data["template_card"]["card_action"] = card_action
                    else:
                        # 使用默认的card_action
                        template_data["template_card"]["card_action"] = {
                            "type": 1,
                            "url": "https://work.weixin.qq.com",
                            "title": "查看详情"
                        }

                    # 发送图文卡片消息
                    response = requests.post(webhook_url, json=template_data, timeout=10)
                    response.raise_for_status()
                    result = response.json()
                    if result.get("errcode") != 0:
                        raise Exception(f"图文卡片消息发送失败：{result.get('errmsg')}（错误码：{result.get('errcode')}）")

                    self.status_label.config(text="状态：图文卡片消息发送成功", foreground="#008000")
                    messagebox.showinfo("发送成功", "图文卡片消息已发送")

            except Exception as e:
                self.status_label.config(text=f"状态：发送失败 - {str(e)}", foreground="#ff0000")
                messagebox.showerror("发送失败", f"错误原因：{str(e)}")
            finally:
                self.send_btn.config(state=tk.NORMAL)

        threading.Thread(target=send, daemon=True).start()

    # ========== Webhook管理方法 ==========
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

        # 按钮区域：确保"确定""取消"都显示
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=tk.E)
        # 确保save_webhook方法存在且参数正确
        ttk.Button(
            btn_frame,
            text="确定",
            command=lambda: self.save_webhook(dialog, name_entry.get(), url_entry.get())
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)

        name_entry.focus_set()  # 默认聚焦名称输入框

    def load_webhooks_from_file(self):
        """从本地JSON文件加载Webhook，返回（数据字典，状态提示文本）"""
        # 获取配置文件路径
        if hasattr(sys, '_MEIPASS'):
            # 打包后的环境
            config_file = os.path.join(sys._MEIPASS, CONFIG_FILENAME)
        else:
            # 开发环境
            config_file = CONFIG_FILENAME
        
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
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
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return {}, "状态：首次运行，创建配置文件"
    
    def save_webhooks_to_file(self):
        """将Webhook记录保存到本地JSON文件，返回是否成功"""
        try:
            # 获取配置文件路径
            if hasattr(sys, '_MEIPASS'):
                # 打包后的环境
                config_file = os.path.join(sys._MEIPASS, CONFIG_FILENAME)
            else:
                # 开发环境
                config_file = CONFIG_FILENAME
            
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.webhooks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("保存失败", f"写入配置文件出错：{str(e)}")
            return False
    
    def save_webhook(self, dialog, name, url):
        """保存Webhook的核心逻辑"""
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

    def update_webhook(self, dialog, url):
        """更新Webhook的核心逻辑"""
        if not url:
            messagebox.showwarning("输入错误", "Webhook地址不能为空！")
            return
        # 保存到内存+本地文件
        self.webhooks[self.current_webhook] = url
        if self.save_webhooks_to_file():
            dialog.destroy()
            self.status_label.config(text="状态：Webhook已更新", foreground="#008000")
            messagebox.showinfo("更新成功", f"Webhook「{self.current_webhook}」已更新")

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


if __name__ == "__main__":
    root = tk.Tk()
    # 设置窗口图标
    root.iconbitmap(r"d:/PythonCode/Tools/icon.ico")
    root.title("企微消息推送")
    app = WeChatRobotSender(root)
    root.mainloop()
