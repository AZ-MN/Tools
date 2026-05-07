import atexit
import base64
import hashlib
import json
import mimetypes
import os
import re
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import requests
from PIL import Image, ImageTk


CONFIG_FILENAME = "webhooks_config.json"
DEFAULT_CARD_IMAGE_URL = "http://oa.zhongtianfitness.com:8080/page/resource/userfile/image/OA00.png"
SUPPORTED_IMAGE_TYPES = [
    ("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"),
    ("所有文件", "*.*"),
]


class WeChatRobotSender:
    DEFAULT_MARKDOWN_TEMPLATE = """# 企微消息 Markdown 示例

## 今日通报
请关注以下内容：

- 支持正文 + 多张图片一起发送
- 本地图片可自动上传图床后嵌入正文
- 也可以选择直接把图片作为后续消息发送
"""

    COLOR_BG = "#eef3f8"
    COLOR_SURFACE = "#ffffff"
    COLOR_SURFACE_SOFT = "#f6f9fc"
    COLOR_HERO = "#102a43"
    COLOR_HERO_ALT = "#1f4d78"
    COLOR_PRIMARY = "#0f6cbd"
    COLOR_PRIMARY_DARK = "#0a4f8a"
    COLOR_ACCENT = "#d9822b"
    COLOR_TEXT = "#102a43"
    COLOR_MUTED = "#6b7c93"
    COLOR_SUCCESS = "#107c10"
    COLOR_WARNING = "#c19c00"
    COLOR_ERROR = "#c42b1c"
    COLOR_BORDER = "#d9e2ec"

    def __init__(self, root):
        self.root = root
        self.root.title("企微消息推送")
        self.root.geometry("1320x880")
        self.root.minsize(1120, 760)
        self.root.configure(bg=self.COLOR_BG)

        self.webhooks = {}
        self.webhook_vars = {}
        self.webhook_checkbuttons = {}
        self.image_paths = []
        self.thumbnail_refs = []
        self.dragging_image_index = None
        self.temp_files = set()
        self.status_reset_timer = None

        self.msg_type_var = tk.StringVar(value="图片")
        self.select_all_var = tk.BooleanVar(value=False)
        self.at_all_var = tk.BooleanVar(value=False)
        self.local_image_mode_var = tk.StringVar(value="图床转URL")

        self.vertical_rows = []
        self.horizontal_rows = []
        self.jump_rows = []

        atexit.register(self.cleanup_temp_files)

        self.configure_styles()
        self.build_layout()
        self.bind_preview_events()

        self.webhooks, load_status = self.load_webhooks_from_file()
        self.refresh_webhook_list()
        self.markdown_text.insert("1.0", self.DEFAULT_MARKDOWN_TEMPLATE)
        self.set_status(load_status, self.COLOR_SUCCESS)
        self.update_webhook_selection_status()
        self.on_tab_changed()
        self.refresh_live_preview()

    def configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=self.COLOR_BG)
        style.configure("Surface.TFrame", background=self.COLOR_SURFACE)
        style.configure("Soft.TFrame", background=self.COLOR_SURFACE_SOFT)
        style.configure("Section.TLabelframe", background=self.COLOR_SURFACE, bordercolor=self.COLOR_BORDER)
        style.configure("Section.TLabelframe.Label", background=self.COLOR_SURFACE, foreground=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Title.TLabel", background=self.COLOR_SURFACE, foreground=self.COLOR_TEXT, font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background=self.COLOR_SURFACE, foreground=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10))
        style.configure("Body.TLabel", background=self.COLOR_SURFACE, foreground=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("Muted.TLabel", background=self.COLOR_SURFACE, foreground=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("TNotebook", background=self.COLOR_SURFACE, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", font=("Microsoft YaHei UI", 10, "bold"), padding=(18, 12), background="#e7eef6", foreground=self.COLOR_MUTED, borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", self.COLOR_PRIMARY), ("active", "#d9e8f8")], foreground=[("selected", "#ffffff"), ("active", self.COLOR_TEXT)])
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 10, "bold"), padding=(14, 9), background=self.COLOR_PRIMARY, foreground="#ffffff", borderwidth=0)
        style.map("Primary.TButton", background=[("active", self.COLOR_PRIMARY_DARK), ("pressed", self.COLOR_PRIMARY_DARK)], foreground=[("disabled", "#c7d3e0")])
        style.configure("Secondary.TButton", font=("Microsoft YaHei UI", 10), padding=(10, 7), background="#e9f2fb", foreground=self.COLOR_PRIMARY, borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#d6e8fb"), ("pressed", "#d6e8fb")])
        style.configure("Danger.TButton", font=("Microsoft YaHei UI", 10), padding=(10, 7), background="#fde7e9", foreground=self.COLOR_ERROR, borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#fbd0d5"), ("pressed", "#fbd0d5")])
        style.configure("TEntry", padding=6, font=("Microsoft YaHei UI", 10))
        style.configure("TCombobox", padding=6, font=("Microsoft YaHei UI", 10))
        style.configure("TRadiobutton", background=self.COLOR_SURFACE, foreground=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("TCheckbutton", background=self.COLOR_SURFACE, foreground=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10))

    def create_card(self, parent, bg=None, border=None, padx=18, pady=18):
        card = tk.Frame(parent, bg=bg or self.COLOR_SURFACE, highlightbackground=border or self.COLOR_BORDER, highlightthickness=1, bd=0)
        inner = tk.Frame(card, bg=bg or self.COLOR_SURFACE)
        inner.pack(fill=tk.BOTH, expand=True, padx=padx, pady=pady)
        return card, inner

    def create_metric_card(self, parent, title, value, note, bg):
        card = tk.Frame(parent, bg=bg, bd=0, highlightthickness=0)
        tk.Label(card, text=title, bg=bg, fg="#d7e7f7" if bg == self.COLOR_HERO else self.COLOR_MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        value_label = tk.Label(card, text=value, bg=bg, fg="#ffffff" if bg == self.COLOR_HERO else self.COLOR_TEXT, font=("Microsoft YaHei UI", 18, "bold"))
        value_label.pack(anchor=tk.W, pady=(6, 2))
        tk.Label(card, text=note, bg=bg, fg="#b9cfe6" if bg == self.COLOR_HERO else self.COLOR_MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        return card, value_label

    def build_layout(self):
        root_frame = ttk.Frame(self.root, style="App.TFrame", padding=18)
        root_frame.pack(fill=tk.BOTH, expand=True)

        hero_card, hero = self.create_card(root_frame, bg=self.COLOR_HERO, border=self.COLOR_HERO, padx=24, pady=22)
        hero_card.pack(fill=tk.X, pady=(0, 18))
        hero.columnconfigure(0, weight=3)
        hero.columnconfigure(1, weight=2)

        left = tk.Frame(hero, bg=self.COLOR_HERO)
        left.grid(row=0, column=0, sticky="nsew")
        tk.Label(left, text="消息编排工作台", bg=self.COLOR_HERO, fg="#ffffff", font=("Microsoft YaHei UI", 24, "bold")).pack(anchor=tk.W)
        tk.Label(left, text="重新设计为卡片式工作流：目标选择、消息编排、资源管理三块并行，减少旧式表单堆叠感。", bg=self.COLOR_HERO, fg="#d7e7f7", font=("Microsoft YaHei UI", 11), justify=tk.LEFT, wraplength=620).pack(anchor=tk.W, pady=(10, 0))

        chips = tk.Frame(left, bg=self.COLOR_HERO)
        chips.pack(anchor=tk.W, pady=(18, 0))
        self.hero_target_chip = tk.Label(chips, text="未选择目标", bg="#1e4a73", fg="#ffffff", font=("Microsoft YaHei UI", 9, "bold"), padx=12, pady=7)
        self.hero_target_chip.pack(side=tk.LEFT)
        self.hero_mode_chip = tk.Label(chips, text="当前模式：图片", bg="#245887", fg="#ffffff", font=("Microsoft YaHei UI", 9, "bold"), padx=12, pady=7)
        self.hero_mode_chip.pack(side=tk.LEFT, padx=(10, 0))

        right = tk.Frame(hero, bg=self.COLOR_HERO)
        right.grid(row=0, column=1, sticky="nsew", padx=(18, 0))
        metrics_row = tk.Frame(right, bg=self.COLOR_HERO)
        metrics_row.pack(fill=tk.X)
        metric_one, self.metric_webhook_value = self.create_metric_card(metrics_row, "推送目标", "0", "已配置的 Webhook", self.COLOR_HERO)
        metric_one.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        metric_two, self.metric_image_value = self.create_metric_card(metrics_row, "图片资源", "0", "本地已选图片", self.COLOR_HERO_ALT)
        metric_two.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))

        workspace = tk.Frame(root_frame, bg=self.COLOR_BG)
        workspace.pack(fill=tk.BOTH, expand=True)
        workspace.columnconfigure(0, weight=28)
        workspace.columnconfigure(1, weight=48)
        workspace.columnconfigure(2, weight=24)
        workspace.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(workspace, bg=self.COLOR_BG)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        self.content = tk.Frame(workspace, bg=self.COLOR_BG)
        self.content.grid(row=0, column=1, sticky="nsew", padx=(0, 14))

        self.utility = tk.Frame(workspace, bg=self.COLOR_BG)
        self.utility.grid(row=0, column=2, sticky="nsew")

        self.build_sidebar()
        self.build_content()
        self.build_utility_panel()

    def build_sidebar(self):
        shell, body = self.create_card(self.sidebar, padx=18, pady=18)
        shell.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="推送目标", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 17, "bold")).pack(anchor=tk.W)
        tk.Label(body, text="左侧只负责选择接收群组与连接管理，不再混入消息编辑。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), justify=tk.LEFT, wraplength=260).pack(anchor=tk.W, pady=(6, 0))

        stats = tk.Frame(body, bg=self.COLOR_SURFACE_SOFT, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        stats.pack(fill=tk.X, pady=(14, 12))
        tk.Label(stats, text="当前仓位", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=12, pady=(10, 2))
        self.sidebar_count_label = tk.Label(stats, text="0 个已配置", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 16, "bold"))
        self.sidebar_count_label.pack(anchor=tk.W, padx=12, pady=(0, 10))

        select_row = tk.Frame(body, bg=self.COLOR_SURFACE)
        select_row.pack(fill=tk.X, pady=(0, 10))
        tk.Checkbutton(select_row, text="全选推送目标", variable=self.select_all_var, command=self.toggle_select_all, bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, activebackground=self.COLOR_SURFACE, activeforeground=self.COLOR_TEXT, selectcolor=self.COLOR_SURFACE, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)

        list_card = tk.Frame(body, bg=self.COLOR_SURFACE_SOFT, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        list_card.pack(fill=tk.BOTH, expand=True)

        self.webhook_canvas = tk.Canvas(list_card, bg=self.COLOR_SURFACE_SOFT, highlightthickness=0, bd=0)
        self.webhook_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        webhook_scrollbar = ttk.Scrollbar(list_card, orient=tk.VERTICAL, command=self.webhook_canvas.yview)
        webhook_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.webhook_canvas.configure(yscrollcommand=webhook_scrollbar.set)

        self.webhook_inner = tk.Frame(self.webhook_canvas, bg=self.COLOR_SURFACE_SOFT)
        self.webhook_canvas_window = self.webhook_canvas.create_window((0, 0), window=self.webhook_inner, anchor="nw")
        self.webhook_inner.bind("<Configure>", self.on_webhook_inner_configure)
        self.webhook_canvas.bind("<Configure>", self.on_webhook_canvas_configure)

        actions = tk.Frame(body, bg=self.COLOR_SURFACE)
        actions.pack(fill=tk.X, pady=(12, 0))

        self.create_sidebar_button(actions, "新增 Webhook", self.add_webhook, self.COLOR_PRIMARY, "#ffffff").pack(fill=tk.X, pady=4)
        self.create_sidebar_button(actions, "编辑 Webhook", self.edit_webhook, self.COLOR_SURFACE_SOFT, self.COLOR_PRIMARY).pack(fill=tk.X, pady=4)
        self.create_sidebar_button(actions, "删除 Webhook", self.delete_webhook, "#fff1f2", self.COLOR_ERROR).pack(fill=tk.X, pady=4)
        self.create_sidebar_button(actions, "测试连接", self.test_webhook, "#fff7e6", "#8a6d00").pack(fill=tk.X, pady=4)

    def build_content(self):
        shell, body = self.create_card(self.content, padx=0, pady=0)
        shell.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(body, bg=self.COLOR_SURFACE)
        header.pack(fill=tk.X, padx=22, pady=(22, 14))
        tk.Label(header, text="消息编排", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        tk.Label(header, text="中间区域专注内容创作。消息类型切换改成主导航，不再藏在下拉框里。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))
        self.selection_label = tk.Label(header, text="当前未选择推送目标", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 11, "bold"))
        self.selection_label.pack(anchor=tk.W, pady=(12, 0))

        notebook_wrap = tk.Frame(body, bg=self.COLOR_SURFACE)
        notebook_wrap.pack(fill=tk.BOTH, expand=True, padx=22)

        self.notebook = ttk.Notebook(notebook_wrap)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", lambda event: self.on_tab_changed())

        self.image_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=20)
        self.markdown_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=20)
        self.news_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=20)
        self.template_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=0)

        self.notebook.add(self.image_tab, text="图片")
        self.notebook.add(self.markdown_tab, text="Markdown")
        self.notebook.add(self.news_tab, text="图文消息")
        self.notebook.add(self.template_tab, text="图文卡片")

        self.build_image_tab()
        self.build_markdown_tab()
        self.build_news_tab()
        self.build_template_tab()

        footer = tk.Frame(body, bg=self.COLOR_SURFACE, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        footer.pack(fill=tk.X, side=tk.BOTTOM, padx=22, pady=(16, 22))

        self.status_label = tk.Label(footer, text="状态：就绪", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10))
        self.status_label.pack(side=tk.LEFT, padx=22, pady=14)

        self.send_btn = ttk.Button(footer, text="发送消息", style="Primary.TButton", command=self.send_message)
        self.send_btn.pack(side=tk.RIGHT, padx=22, pady=10)

    def build_utility_panel(self):
        self.build_common_controls(self.utility)
        self.build_preview_panel(self.utility)
        self.build_assets_panel(self.utility)

    def build_preview_panel(self, parent):
        card, body = self.create_card(parent, padx=16, pady=16)
        card.pack(fill=tk.BOTH, expand=False, pady=(0, 14))
        tk.Label(body, text="实时预览", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 16, "bold")).pack(anchor=tk.W)
        tk.Label(body, text="根据当前页签动态展示消息摘要，减少盲填。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), wraplength=280, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))

        header = tk.Frame(body, bg=self.COLOR_SURFACE_SOFT, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        header.pack(fill=tk.X, pady=(14, 12))
        tk.Label(header, text="当前预览类型", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=12, pady=(10, 2))
        self.preview_title_label = tk.Label(header, text="图片", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 12, "bold"))
        self.preview_title_label.pack(anchor=tk.W, padx=12, pady=(0, 10))

        visual_shell = tk.Frame(body, bg="#f8fbff", highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        visual_shell.pack(fill=tk.X, pady=(0, 12))
        self.preview_visual = tk.Frame(visual_shell, bg="#f8fbff")
        self.preview_visual.pack(fill=tk.X, padx=12, pady=12)
        self.preview_visual_mode = tk.Label(self.preview_visual, text="图片模式", bg="#f8fbff", fg=self.COLOR_PRIMARY, font=("Microsoft YaHei UI", 9, "bold"))
        self.preview_visual_mode.pack(anchor=tk.W)
        self.preview_visual_heading = tk.Label(self.preview_visual, text="等待输入", bg="#f8fbff", fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 13, "bold"), wraplength=260, justify=tk.LEFT)
        self.preview_visual_heading.pack(anchor=tk.W, pady=(8, 4))
        self.preview_visual_desc = tk.Label(self.preview_visual, text="右侧会展示当前消息结构和摘要。", bg="#f8fbff", fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9), wraplength=260, justify=tk.LEFT)
        self.preview_visual_desc.pack(anchor=tk.W)
        self.preview_badge_row = tk.Frame(self.preview_visual, bg="#f8fbff")
        self.preview_badge_row.pack(anchor=tk.W, pady=(10, 0))
        self.preview_section_list = tk.Frame(self.preview_visual, bg="#f8fbff")
        self.preview_section_list.pack(fill=tk.X, pady=(10, 0))

        self.preview_text = tk.Text(body, height=14, font=("Consolas", 9), bg="#f8fbff", fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief=tk.FLAT, padx=10, pady=10, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        self.preview_text.config(state=tk.DISABLED)

    def build_image_tab(self):
        top = tk.Frame(self.image_tab, bg=self.COLOR_SURFACE)
        top.pack(fill=tk.X)
        tk.Label(top, text="图片批量推送", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        tk.Label(top, text="适合直接把多张图片发到群里。每张图片会独立成为一条 image 消息，减少卡片或 Markdown 的兼容限制。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), wraplength=760, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))

        grid = tk.Frame(self.image_tab, bg=self.COLOR_SURFACE)
        grid.pack(fill=tk.BOTH, expand=True, pady=(18, 0))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        card_one, inner_one = self.create_card(grid, bg=self.COLOR_SURFACE_SOFT, padx=16, pady=16)
        card_one.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(inner_one, text="适用场景", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)
        for line in ["活动返图批量推送", "海报和截图集中下发", "不需要把文案塞入同一条消息"]:
            tk.Label(inner_one, text=f"• {line}", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(10, 0))

        card_two, inner_two = self.create_card(grid, bg="#fff7e6", border="#f7d9a7", padx=16, pady=16)
        card_two.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(inner_two, text="行为说明", bg="#fff7e6", fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)
        tk.Label(inner_two, text="本地图片会自动压缩到企业微信允许范围。网络图片会先下载后编码，再统一发送。", bg="#fff7e6", fg="#8a6d00", font=("Microsoft YaHei UI", 10), wraplength=320, justify=tk.LEFT).pack(anchor=tk.W, pady=(10, 0))

    def build_markdown_tab(self):
        header = tk.Frame(self.markdown_tab, bg=self.COLOR_SURFACE)
        header.pack(fill=tk.X)
        tk.Label(header, text="Markdown 图文合发", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        tk.Label(header, text="这是正文编辑主舞台。选“图床转URL”时，多张图片会自动嵌入到同一消息体；选“直接发送”时，图片会在正文后补发。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), wraplength=780, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))

        editor, editor_body = self.create_card(self.markdown_tab, bg=self.COLOR_SURFACE_SOFT, padx=18, pady=18)
        editor.pack(fill=tk.BOTH, expand=True, pady=(18, 0))

        toolbar = tk.Frame(editor_body, bg=self.COLOR_SURFACE_SOFT)
        toolbar.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(toolbar, text="加载模板", style="Secondary.TButton", command=self.load_markdown_template).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="清空正文", style="Secondary.TButton", command=self.clear_markdown_text).pack(side=tk.LEFT, padx=(10, 0))

        text_wrap = tk.Frame(editor_body, bg=self.COLOR_SURFACE_SOFT)
        text_wrap.pack(fill=tk.BOTH, expand=True)
        self.markdown_text = tk.Text(text_wrap, wrap=tk.WORD, height=16, font=("Consolas", 11), bg="#ffffff", fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief=tk.FLAT, padx=16, pady=16)
        self.markdown_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(text_wrap, orient=tk.VERTICAL, command=self.markdown_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.markdown_text.configure(yscrollcommand=scrollbar.set)

    def build_news_tab(self):
        header = tk.Frame(self.news_tab, bg=self.COLOR_SURFACE)
        header.pack(fill=tk.X)
        tk.Label(header, text="单图文消息", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        tk.Label(header, text="用于一条标题、一段描述、一个落地页链接的轻量通知。封面图只取一张，多余图片会自动补发。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), wraplength=760, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))

        form = ttk.LabelFrame(self.news_tab, text="图文消息字段", style="Section.TLabelframe", padding=16)
        form.pack(fill=tk.BOTH, expand=True, pady=(18, 0))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="标题", style="Body.TLabel").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.news_title_entry = ttk.Entry(form)
        self.news_title_entry.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(form, text="描述", style="Body.TLabel").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.news_desc_entry = ttk.Entry(form)
        self.news_desc_entry.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(form, text="跳转链接", style="Body.TLabel").grid(row=2, column=0, sticky=tk.W, pady=6)
        self.news_url_entry = ttk.Entry(form)
        self.news_url_entry.grid(row=2, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(form, text="图片链接", style="Body.TLabel").grid(row=3, column=0, sticky=tk.W, pady=6)
        self.news_picurl_entry = ttk.Entry(form)
        self.news_picurl_entry.grid(row=3, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(form, text="未填写图片链接时，会优先使用共享图片区的第一张网络图片；如果选择了本地图片且模式为“图床转URL”，会自动上传第一张本地图片作为封面。其他图片将作为独立 image 消息继续发送。", style="Muted.TLabel", wraplength=820, justify=tk.LEFT).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    def build_template_tab(self):
        outer = ttk.Frame(self.template_tab, style="Surface.TFrame")
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, bg=self.COLOR_SURFACE, highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        self.template_inner = ttk.Frame(canvas, style="Surface.TFrame", padding=18)
        self.template_window = canvas.create_window((0, 0), window=self.template_inner, anchor="nw")
        self.template_inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfig(self.template_window, width=event.width))

        banner = tk.Frame(self.template_inner, bg=self.COLOR_SURFACE)
        banner.pack(fill=tk.X, pady=(0, 14))
        tk.Label(banner, text="图文卡片编排", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 18, "bold")).pack(anchor=tk.W)
        tk.Label(banner, text="把复杂字段拆成更轻的模块。头图、图文区、正文块、跳转块分别管理，减少长表单压迫感。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), wraplength=760, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))

        summary_row = tk.Frame(self.template_inner, bg=self.COLOR_SURFACE)
        summary_row.pack(fill=tk.X, pady=(0, 14))
        summary_row.columnconfigure(0, weight=1)
        summary_row.columnconfigure(1, weight=1)

        tip_card, tip_body = self.create_card(summary_row, bg=self.COLOR_SURFACE_SOFT, padx=16, pady=16)
        tip_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(tip_body, text="推荐编排", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)
        for line in ["主标题放一句最核心的结论", "头图承载视觉焦点", "图文区补充一张关键图片", "跳转按钮只保留 1 到 2 个"]:
            tk.Label(tip_body, text=f"• {line}", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10)).pack(anchor=tk.W, pady=(8, 0))

        warn_card, warn_body = self.create_card(summary_row, bg="#fff7e6", border="#f7d9a7", padx=16, pady=16)
        warn_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(warn_body, text="能力边界", bg="#fff7e6", fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 12, "bold")).pack(anchor=tk.W)
        tk.Label(warn_body, text="企业微信卡片不是多图瀑布流。稳定可控的是头图 + 图文区图片，其余图片程序会在卡片后补发。", bg="#fff7e6", fg="#8a6d00", font=("Microsoft YaHei UI", 10), wraplength=320, justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 0))

        content_grid = tk.Frame(self.template_inner, bg=self.COLOR_SURFACE)
        content_grid.pack(fill=tk.BOTH, expand=True)
        content_grid.columnconfigure(0, weight=1)
        content_grid.columnconfigure(1, weight=1)

        left_column = tk.Frame(content_grid, bg=self.COLOR_SURFACE)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_column = tk.Frame(content_grid, bg=self.COLOR_SURFACE)
        right_column.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        base = ttk.LabelFrame(left_column, text="卡片基础信息", style="Section.TLabelframe", padding=14)
        base.pack(fill=tk.X)
        base.columnconfigure(1, weight=1)

        ttk.Label(base, text="主标题", style="Body.TLabel").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.card_title_entry = ttk.Entry(base)
        self.card_title_entry.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(base, text="主标题描述", style="Body.TLabel").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.card_desc_entry = ttk.Entry(base)
        self.card_desc_entry.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(base, text="头图 URL", style="Body.TLabel").grid(row=2, column=0, sticky=tk.W, pady=6)
        self.card_image_entry = ttk.Entry(base)
        self.card_image_entry.grid(row=2, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(base, text="若不填写头图 URL，会优先取共享图片区的第一张图片；没有可用图片时会落回默认头图。", style="Muted.TLabel", wraplength=360, justify=tk.LEFT).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        image_area = ttk.LabelFrame(left_column, text="图文区（可选）", style="Section.TLabelframe", padding=14)
        image_area.pack(fill=tk.X, pady=(14, 0))
        image_area.columnconfigure(1, weight=1)

        ttk.Label(image_area, text="标题", style="Body.TLabel").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.card_image_area_title_entry = ttk.Entry(image_area)
        self.card_image_area_title_entry.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(image_area, text="描述", style="Body.TLabel").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.card_image_area_desc_entry = ttk.Entry(image_area)
        self.card_image_area_desc_entry.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(image_area, text="图片 URL", style="Body.TLabel").grid(row=2, column=0, sticky=tk.W, pady=6)
        self.card_image_area_url_entry = ttk.Entry(image_area)
        self.card_image_area_url_entry.grid(row=2, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        ttk.Label(image_area, text="跳转链接", style="Body.TLabel").grid(row=3, column=0, sticky=tk.W, pady=6)
        self.card_image_area_jump_entry = ttk.Entry(image_area)
        self.card_image_area_jump_entry.grid(row=3, column=1, sticky=tk.EW, pady=6, padx=(12, 0))

        self.vertical_section = ttk.LabelFrame(right_column, text="垂直内容列表", style="Section.TLabelframe", padding=14)
        self.vertical_section.pack(fill=tk.X, pady=(14, 0))
        self.vertical_rows_container = ttk.Frame(self.vertical_section, style="Surface.TFrame")
        self.vertical_rows_container.pack(fill=tk.X)
        ttk.Button(self.vertical_section, text="新增垂直内容", style="Secondary.TButton", command=self.add_vertical_row).pack(anchor=tk.W, pady=(10, 0))

        self.horizontal_section = ttk.LabelFrame(right_column, text="水平内容列表", style="Section.TLabelframe", padding=14)
        self.horizontal_section.pack(fill=tk.X, pady=(14, 0))
        self.horizontal_rows_container = ttk.Frame(self.horizontal_section, style="Surface.TFrame")
        self.horizontal_rows_container.pack(fill=tk.X)
        ttk.Button(self.horizontal_section, text="新增水平内容", style="Secondary.TButton", command=self.add_horizontal_row).pack(anchor=tk.W, pady=(10, 0))

        self.jump_section = ttk.LabelFrame(left_column, text="跳转按钮", style="Section.TLabelframe", padding=14)
        self.jump_section.pack(fill=tk.X, pady=(14, 0))
        self.jump_rows_container = ttk.Frame(self.jump_section, style="Surface.TFrame")
        self.jump_rows_container.pack(fill=tk.X)
        ttk.Button(self.jump_section, text="新增跳转按钮", style="Secondary.TButton", command=self.add_jump_row).pack(anchor=tk.W, pady=(10, 0))

        self.add_vertical_row()
        self.add_horizontal_row()
        self.add_jump_row()

    def build_common_controls(self, parent):
        card, body = self.create_card(parent, padx=16, pady=16)
        card.pack(fill=tk.X, pady=(0, 14))
        tk.Label(body, text="发送设置", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 16, "bold")).pack(anchor=tk.W)
        tk.Label(body, text="把会影响发送行为的开关单独收拢，避免混进正文编辑区。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), justify=tk.LEFT, wraplength=280).pack(anchor=tk.W, pady=(6, 0))

        field = tk.Frame(body, bg=self.COLOR_SURFACE)
        field.pack(fill=tk.X, pady=(14, 0))
        tk.Label(field, text="@用户手机号", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)
        self.at_entry = ttk.Entry(field)
        self.at_entry.pack(fill=tk.X, pady=(8, 0))
        self.at_all_check = ttk.Checkbutton(field, text="@所有人", variable=self.at_all_var)
        self.at_all_check.pack(anchor=tk.W, pady=(8, 0))

        mode = tk.Frame(body, bg=self.COLOR_SURFACE_SOFT, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        mode.pack(fill=tk.X, pady=(14, 0))
        tk.Label(mode, text="本地图片处理模式", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W, padx=12, pady=(10, 6))
        modes = tk.Frame(mode, bg=self.COLOR_SURFACE_SOFT)
        modes.pack(fill=tk.X, padx=12, pady=(0, 10))
        ttk.Radiobutton(modes, text="图床转URL", variable=self.local_image_mode_var, value="图床转URL").pack(side=tk.LEFT)
        ttk.Radiobutton(modes, text="直接发送", variable=self.local_image_mode_var, value="直接发送").pack(side=tk.LEFT, padx=(12, 0))

        tk.Label(body, text="提示：Markdown 模式下，图床转URL会把多图嵌入同一条消息；直接发送则正文先发、图片后补。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9), wraplength=280, justify=tk.LEFT).pack(anchor=tk.W, pady=(12, 0))

    def build_assets_panel(self, parent):
        card, body = self.create_card(parent, padx=16, pady=16)
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(body, text="资源池", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 16, "bold")).pack(anchor=tk.W)
        tk.Label(body, text="本地图片和网络图片统一放到这里复用。右侧独立出来后，主编辑区会更干净。", bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 10), justify=tk.LEFT, wraplength=280).pack(anchor=tk.W, pady=(6, 0))

        stats = tk.Frame(body, bg=self.COLOR_SURFACE_SOFT, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        stats.pack(fill=tk.X, pady=(14, 12))
        tk.Label(stats, text="资源概况", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=12, pady=(10, 2))
        self.image_summary_label = tk.Label(stats, text="未选择本地图片", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 11, "bold"))
        self.image_summary_label.pack(anchor=tk.W, padx=12, pady=(0, 10))

        action_bar = tk.Frame(body, bg=self.COLOR_SURFACE)
        action_bar.pack(fill=tk.X)
        ttk.Button(action_bar, text="添加图片", style="Secondary.TButton", command=self.select_images).pack(side=tk.LEFT)
        ttk.Button(action_bar, text="移除选中", style="Secondary.TButton", command=self.remove_selected_images).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(action_bar, text="上移", style="Secondary.TButton", command=lambda: self.move_selected_images(-1)).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(action_bar, text="下移", style="Secondary.TButton", command=lambda: self.move_selected_images(1)).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(action_bar, text="清空", style="Danger.TButton", command=self.clear_images).pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(body, text="缩略图预览", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W, pady=(14, 0))
        preview_shell = tk.Frame(body, bg=self.COLOR_SURFACE_SOFT, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        preview_shell.pack(fill=tk.X, pady=(8, 0))
        self.preview_canvas = tk.Canvas(preview_shell, bg=self.COLOR_SURFACE_SOFT, highlightthickness=0, bd=0, height=112)
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll = ttk.Scrollbar(preview_shell, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        preview_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.preview_canvas.configure(xscrollcommand=preview_scroll.set)
        self.preview_inner = tk.Frame(self.preview_canvas, bg=self.COLOR_SURFACE_SOFT)
        self.preview_window = self.preview_canvas.create_window((0, 0), window=self.preview_inner, anchor="nw")
        self.preview_inner.bind("<Configure>", lambda event: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all")))
        self.preview_canvas.bind("<Configure>", lambda event: self.preview_canvas.itemconfig(self.preview_window, height=event.height))

        list_wrap = tk.Frame(body, bg=self.COLOR_SURFACE_SOFT, highlightbackground=self.COLOR_BORDER, highlightthickness=1)
        list_wrap.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.image_listbox = tk.Listbox(list_wrap, height=10, selectmode=tk.EXTENDED, font=("Microsoft YaHei UI", 10), bg="#ffffff", fg=self.COLOR_TEXT, selectbackground="#cfe8ff", relief=tk.FLAT, activestyle="none", highlightthickness=0, bd=0)
        self.image_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.image_listbox.bind("<ButtonPress-1>", self.on_image_listbox_press)
        self.image_listbox.bind("<B1-Motion>", self.on_image_listbox_drag)
        self.image_listbox.bind("<ButtonRelease-1>", self.on_image_listbox_release)

        tk.Label(body, text="网络图片 URL（每行一条）", bg=self.COLOR_SURFACE, fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W, pady=(14, 0))
        self.net_image_text = tk.Text(body, height=7, font=("Consolas", 10), bg="#f8fbff", fg=self.COLOR_TEXT, insertbackground=self.COLOR_TEXT, relief=tk.FLAT, padx=10, pady=10)
        self.net_image_text.pack(fill=tk.X, pady=(8, 0))

    def create_sidebar_button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief=tk.FLAT, bd=0, font=("Microsoft YaHei UI", 10, "bold" if text == "新增 Webhook" else "normal"), padx=12, pady=10, cursor="hand2")

    def on_tab_changed(self):
        index = self.notebook.index(self.notebook.select())
        tab_text = self.notebook.tab(index, "text")
        self.msg_type_var.set(tab_text)
        self.hero_mode_chip.config(text=f"当前模式：{tab_text}")
        if tab_text == "Markdown":
            self.at_all_check.state(["!disabled"])
            self.at_entry.state(["!disabled"])
        else:
            self.at_all_check.state(["disabled"])
            self.at_entry.state(["disabled"])
        self.refresh_live_preview()

    def set_status(self, text, color=None, auto_reset=False):
        def update():
            self.status_label.config(text=text, fg=color or self.COLOR_MUTED)
            if auto_reset:
                self.reset_status_after_delay()

        self.root.after(0, update)

    def reset_status_after_delay(self):
        if self.status_reset_timer:
            self.root.after_cancel(self.status_reset_timer)
        self.status_reset_timer = self.root.after(3000, lambda: self.status_label.config(text="状态：就绪", fg=self.COLOR_MUTED))

    def get_config_path(self):
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(os.path.expanduser("~"), f".{CONFIG_FILENAME}")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)

    def load_webhooks_from_file(self):
        config_file = self.get_config_path()
        try:
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, dict):
                    return data, f"状态：已加载 {len(data)} 个 Webhook"
                return {}, "状态：配置格式异常，已重置"

            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as file:
                json.dump({}, file, ensure_ascii=False, indent=2)
            return {}, "状态：已创建配置文件"
        except Exception as error:
            messagebox.showerror("加载失败", f"读取配置文件失败：{error}")
            return {}, "状态：配置加载失败"

    def save_webhooks_to_file(self):
        config_file = self.get_config_path()
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as file:
                json.dump(self.webhooks, file, ensure_ascii=False, indent=2)
            return True
        except Exception as error:
            messagebox.showerror("保存失败", f"保存配置文件失败：{error}")
            return False

    def on_webhook_inner_configure(self, _event):
        self.webhook_canvas.configure(scrollregion=self.webhook_canvas.bbox("all"))

    def on_webhook_canvas_configure(self, event):
        self.webhook_canvas.itemconfig(self.webhook_canvas_window, width=event.width)

    def toggle_select_all(self):
        selected = self.select_all_var.get()
        for variable in self.webhook_vars.values():
            variable.set(selected)
        self.update_webhook_selection_status()

    def on_webhook_checkbox_change(self, *_args):
        self.update_webhook_selection_status()

    def get_selected_webhooks(self):
        return [name for name, variable in self.webhook_vars.items() if variable.get()]

    def update_webhook_selection_status(self):
        selected = self.get_selected_webhooks()
        total = len(self.webhook_vars)
        self.sidebar_count_label.config(text=f"{total} 个已配置")
        self.metric_webhook_value.config(text=str(total))
        all_selected = total > 0 and len(selected) == total
        self.select_all_var.set(all_selected)

        if not selected:
            self.selection_label.config(text="当前未选择推送目标")
            self.hero_target_chip.config(text="未选择目标")
            self.send_btn.state(["disabled"])
            return

        if len(selected) == 1:
            self.selection_label.config(text=f"当前推送目标：{selected[0]}")
            self.hero_target_chip.config(text=f"目标：{selected[0]}")
        else:
            self.selection_label.config(text=f"当前推送目标：已选择 {len(selected)} 个 Webhook")
            self.hero_target_chip.config(text=f"已选 {len(selected)} 个目标")
        self.send_btn.state(["!disabled"])

    def refresh_webhook_list(self):
        for child in self.webhook_inner.winfo_children():
            child.destroy()
        self.webhook_vars.clear()
        self.webhook_checkbuttons.clear()

        for name in self.webhooks:
            row = tk.Frame(self.webhook_inner, bg=self.COLOR_SURFACE_SOFT, padx=8, pady=4)
            row.pack(fill=tk.X, padx=8, pady=6)

            variable = tk.BooleanVar(value=False)
            variable.trace_add("write", self.on_webhook_checkbox_change)
            self.webhook_vars[name] = variable

            checkbox = tk.Checkbutton(row, text=name, variable=variable, bg="#ffffff", fg=self.COLOR_TEXT, activebackground="#ffffff", activeforeground=self.COLOR_TEXT, selectcolor="#ffffff", relief=tk.FLAT, anchor="w", font=("Microsoft YaHei UI", 10, "bold"), padx=12, pady=10, highlightthickness=1, highlightbackground=self.COLOR_BORDER)
            checkbox.pack(fill=tk.X)
            self.webhook_checkbuttons[name] = checkbox

        if self.webhook_vars:
            first_name = next(iter(self.webhook_vars))
            self.webhook_vars[first_name].set(True)
        self.update_webhook_selection_status()

    def open_webhook_dialog(self, title, default_name="", default_url="", readonly_name=False, on_submit=None):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("620x240")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.COLOR_SURFACE)

        frame = ttk.Frame(dialog, style="Surface.TFrame", padding=18)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Webhook 名称", style="Body.TLabel").grid(row=0, column=0, sticky=tk.W, pady=8)
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=8, padx=(12, 0))
        name_entry.insert(0, default_name)
        if readonly_name:
            name_entry.state(["disabled"])

        ttk.Label(frame, text="Webhook 地址", style="Body.TLabel").grid(row=1, column=0, sticky=tk.W, pady=8)
        url_entry = ttk.Entry(frame)
        url_entry.grid(row=1, column=1, sticky=tk.EW, pady=8, padx=(12, 0))
        url_entry.insert(0, default_url)

        btns = ttk.Frame(frame, style="Surface.TFrame")
        btns.grid(row=2, column=0, columnspan=2, sticky=tk.E, pady=(18, 0))
        ttk.Button(btns, text="取消", style="Secondary.TButton", command=dialog.destroy).pack(side=tk.RIGHT)
        ttk.Button(btns, text="保存", style="Primary.TButton", command=lambda: on_submit(dialog, name_entry.get().strip(), url_entry.get().strip()) if on_submit else None).pack(side=tk.RIGHT, padx=(0, 10))

        url_entry.focus_set()

    def add_webhook(self):
        self.open_webhook_dialog("新增 Webhook", on_submit=self.save_webhook)

    def save_webhook(self, dialog, name, url):
        if not name or not url:
            messagebox.showwarning("输入不完整", "Webhook 名称和地址不能为空。")
            return
        if name in self.webhooks:
            messagebox.showwarning("名称重复", f"Webhook “{name}” 已存在。")
            return
        self.webhooks[name] = url
        if self.save_webhooks_to_file():
            dialog.destroy()
            self.refresh_webhook_list()
            self.set_status(f"状态：Webhook “{name}” 已新增", self.COLOR_SUCCESS, auto_reset=True)

    def edit_webhook(self):
        selected = self.get_selected_webhooks()
        if not selected:
            messagebox.showinfo("提示", "请先选择一个 Webhook。")
            return
        name = selected[0]
        self.open_webhook_dialog("编辑 Webhook", name, self.webhooks.get(name, ""), True, self.update_webhook)

    def update_webhook(self, dialog, name, url):
        if not url:
            messagebox.showwarning("输入不完整", "Webhook 地址不能为空。")
            return
        self.webhooks[name] = url
        if self.save_webhooks_to_file():
            dialog.destroy()
            self.set_status(f"状态：Webhook “{name}” 已更新", self.COLOR_SUCCESS, auto_reset=True)

    def delete_webhook(self):
        selected = self.get_selected_webhooks()
        if not selected:
            messagebox.showinfo("提示", "请先选择要删除的 Webhook。")
            return
        confirm = messagebox.askyesno("确认删除", f"确定删除以下 {len(selected)} 个 Webhook 吗？\n\n" + "\n".join(selected))
        if not confirm:
            return
        for name in selected:
            self.webhooks.pop(name, None)
        if self.save_webhooks_to_file():
            self.refresh_webhook_list()
            self.set_status(f"状态：已删除 {len(selected)} 个 Webhook", self.COLOR_SUCCESS, auto_reset=True)

    def test_webhook(self):
        selected = self.get_selected_webhooks()
        if not selected:
            messagebox.showinfo("提示", "请先选择一个 Webhook。")
            return

        webhook_name = selected[0]
        webhook_url = self.webhooks[webhook_name]
        self.set_status(f"状态：正在测试 {webhook_name} ...", self.COLOR_WARNING)

        def worker():
            try:
                payload = {"msgtype": "markdown", "markdown": {"content": "# Webhook 测试成功\n这是一条测试消息。\n<@all>"}}
                self.post_payload(webhook_url, payload)
                self.root.after(0, lambda: messagebox.showinfo("测试成功", f"Webhook {webhook_name} 连接正常。"))
                self.set_status(f"状态：测试连接成功（{webhook_name}）", self.COLOR_SUCCESS, auto_reset=True)
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("测试失败", str(error)))
                self.set_status(f"状态：测试失败 - {error}", self.COLOR_ERROR, auto_reset=True)

        threading.Thread(target=worker, daemon=True).start()

    def load_markdown_template(self):
        self.markdown_text.delete("1.0", tk.END)
        self.markdown_text.insert("1.0", self.DEFAULT_MARKDOWN_TEMPLATE)
        self.set_status("状态：已加载 Markdown 模板", self.COLOR_SUCCESS, auto_reset=True)

    def clear_markdown_text(self):
        self.markdown_text.delete("1.0", tk.END)

    def select_images(self):
        file_paths = filedialog.askopenfilenames(title="选择图片文件", filetypes=SUPPORTED_IMAGE_TYPES)
        if not file_paths:
            return

        existing = set(self.image_paths)
        added = 0
        for path in file_paths:
            if path not in existing:
                self.image_paths.append(path)
                existing.add(path)
                added += 1

        self.refresh_image_list()
        self.set_status(f"状态：已新增 {added} 张图片", self.COLOR_SUCCESS, auto_reset=True)

    def refresh_image_list(self):
        self.image_listbox.delete(0, tk.END)
        for path in self.image_paths:
            self.image_listbox.insert(tk.END, os.path.basename(path))

        if self.image_paths:
            self.image_summary_label.config(text=f"已选择 {len(self.image_paths)} 张本地图片")
        else:
            self.image_summary_label.config(text="未选择本地图片")
        self.metric_image_value.config(text=str(len(self.image_paths)))
        self.refresh_image_previews()
        self.refresh_live_preview()

    def build_thumbnail_card(self, parent, image_path):
        tile = tk.Frame(parent, bg="#ffffff", highlightbackground=self.COLOR_BORDER, highlightthickness=1, width=88, height=88)
        tile.pack(side=tk.LEFT, padx=8, pady=10)
        tile.pack_propagate(False)

        try:
            with Image.open(image_path) as image:
                preview = image.copy()
                preview.thumbnail((72, 72))
                photo = ImageTk.PhotoImage(preview)
            self.thumbnail_refs.append(photo)
            label = tk.Label(tile, image=photo, bg="#ffffff")
            label.pack(expand=True)
        except Exception:
            fallback = tk.Label(tile, text="无预览", bg="#ffffff", fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 8))
            fallback.pack(expand=True)

        caption = tk.Label(parent, text=os.path.basename(image_path)[:10], bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 8))
        caption.pack(side=tk.LEFT, padx=(0, 4))

    def refresh_image_previews(self):
        self.thumbnail_refs = []
        for child in self.preview_inner.winfo_children():
            child.destroy()

        if not self.image_paths:
            empty = tk.Label(self.preview_inner, text="添加本地图片后，这里会显示缩略图画廊。", bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9))
            empty.pack(anchor=tk.W, padx=12, pady=18)
            return

        for image_path in self.image_paths:
            group = tk.Frame(self.preview_inner, bg=self.COLOR_SURFACE_SOFT)
            group.pack(side=tk.LEFT, padx=6, pady=6)
            tile = tk.Frame(group, bg="#ffffff", highlightbackground=self.COLOR_BORDER, highlightthickness=1, width=86, height=86)
            tile.pack()
            tile.pack_propagate(False)

            try:
                with Image.open(image_path) as image:
                    preview = image.copy()
                    preview.thumbnail((70, 70))
                    photo = ImageTk.PhotoImage(preview)
                self.thumbnail_refs.append(photo)
                image_label = tk.Label(tile, image=photo, bg="#ffffff", cursor="hand2")
                image_label.pack(expand=True)
                image_label.bind("<Button-1>", lambda _event, path=image_path: self.open_image_preview(path))
                tile.bind("<Button-1>", lambda _event, path=image_path: self.open_image_preview(path))
            except Exception:
                tk.Label(tile, text="无预览", bg="#ffffff", fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 8)).pack(expand=True)

            caption = tk.Label(group, text=os.path.basename(image_path)[:10], bg=self.COLOR_SURFACE_SOFT, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 8), cursor="hand2")
            caption.pack(pady=(6, 0))
            caption.bind("<Button-1>", lambda _event, path=image_path: self.open_image_preview(path))

    def open_image_preview(self, image_path):
        if not os.path.exists(image_path):
            messagebox.showwarning("预览失败", "图片文件不存在或已被移动。")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(os.path.basename(image_path))
        dialog.geometry("920x700")
        dialog.configure(bg=self.COLOR_SURFACE)
        dialog.transient(self.root)

        container = tk.Frame(dialog, bg=self.COLOR_SURFACE)
        container.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        meta = tk.Label(container, text=image_path, bg=self.COLOR_SURFACE, fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 9), wraplength=860, justify=tk.LEFT)
        meta.pack(anchor=tk.W, pady=(0, 12))

        canvas = tk.Canvas(container, bg="#0b1f33", highlightthickness=0, bd=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        try:
            with Image.open(image_path) as image:
                preview = image.copy()
                preview.thumbnail((860, 580))
                photo = ImageTk.PhotoImage(preview)
            self.thumbnail_refs.append(photo)
            canvas.create_image(430, 290, image=photo)
        except Exception as error:
            canvas.create_text(430, 290, text=f"预览失败\n{error}", fill="#ffffff", font=("Microsoft YaHei UI", 12))

    def bind_preview_events(self):
        self.markdown_text.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())
        self.net_image_text.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())

        simple_entries = [
            self.at_entry,
            self.news_title_entry,
            self.news_desc_entry,
            self.news_url_entry,
            self.news_picurl_entry,
            self.card_title_entry,
            self.card_desc_entry,
            self.card_image_entry,
            self.card_image_area_title_entry,
            self.card_image_area_desc_entry,
            self.card_image_area_url_entry,
            self.card_image_area_jump_entry,
        ]
        for entry in simple_entries:
            entry.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())

        self.at_all_var.trace_add("write", lambda *_args: self.schedule_preview_refresh())
        self.local_image_mode_var.trace_add("write", lambda *_args: self.schedule_preview_refresh())

    def schedule_preview_refresh(self):
        self.root.after_idle(self.refresh_live_preview)

    def set_preview_badges(self, badges):
        for child in self.preview_badge_row.winfo_children():
            child.destroy()
        for text, bg, fg in badges:
            tk.Label(self.preview_badge_row, text=text, bg=bg, fg=fg, font=("Microsoft YaHei UI", 8, "bold"), padx=8, pady=4).pack(side=tk.LEFT, padx=(0, 6))

    def set_preview_sections(self, sections):
        for child in self.preview_section_list.winfo_children():
            child.destroy()
        for label, value in sections:
            row = tk.Frame(self.preview_section_list, bg="#ffffff", highlightbackground=self.COLOR_BORDER, highlightthickness=1)
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=label, bg="#ffffff", fg=self.COLOR_MUTED, font=("Microsoft YaHei UI", 8, "bold")).pack(anchor=tk.W, padx=8, pady=(6, 2))
            tk.Label(row, text=value, bg="#ffffff", fg=self.COLOR_TEXT, font=("Microsoft YaHei UI", 9), wraplength=236, justify=tk.LEFT).pack(anchor=tk.W, padx=8, pady=(0, 6))

    def set_preview_visual(self, mode, heading, desc, badges, sections):
        self.preview_visual_mode.config(text=mode)
        self.preview_visual_heading.config(text=heading)
        self.preview_visual_desc.config(text=desc)
        self.set_preview_badges(badges)
        self.set_preview_sections(sections)

    def set_preview_text(self, title, content):
        self.preview_title_label.config(text=title)
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", content)
        self.preview_text.config(state=tk.DISABLED)

    def build_markdown_preview_text(self):
        content = self.markdown_text.get("1.0", tk.END).strip()
        local_images, network_urls = self.prepare_shared_images()
        mentions = self.get_mentioned_mobiles()
        lines = [
            "模式：Markdown 图文合发",
            f"本地图片：{len(local_images)} 张",
            f"网络图片：{len(network_urls)} 张",
            f"图片处理：{self.local_image_mode_var.get()}",
            f"@用户：{', '.join(mentions) if mentions else '无'}",
            f"@所有人：{'是' if self.at_all_var.get() else '否'}",
            "",
            "正文预览：",
            content[:1200] if content else "（暂无内容）",
        ]
        return "\n".join(lines)

    def build_markdown_preview_visual(self):
        content = self.markdown_text.get("1.0", tk.END).strip()
        first_line = next((line.strip("# ").strip() for line in content.splitlines() if line.strip()), "Markdown 消息")
        local_images, network_urls = self.prepare_shared_images()
        lines = [line for line in content.splitlines() if line.strip()]
        heading_count = sum(1 for line in lines if line.lstrip().startswith("#"))
        quote_count = sum(1 for line in lines if line.lstrip().startswith(">"))
        list_count = sum(1 for line in lines if re.match(r"^\s*([-*]|\d+\.)\s+", line))
        badges = [
            (f"本地 {len(local_images)} 张", "#e8f1fb", self.COLOR_PRIMARY),
            (f"网络 {len(network_urls)} 张", "#eef7ee", self.COLOR_SUCCESS),
        ]
        sections = [
            ("标题层级", f"检测到 {heading_count} 个标题行"),
            ("引用 / 列表", f"引用 {quote_count} 处，列表 {list_count} 处"),
            ("正文片段", (content[:140] + "...") if len(content) > 140 else (content or "暂无正文内容")),
        ]
        return ("Markdown 实时卡片", first_line, "正文、标题、引用和图片数量会在这里形成结构化预览。", badges, sections)

    def build_image_preview_text(self):
        local_images, network_urls = self.prepare_shared_images()
        lines = [
            "模式：图片批量推送",
            f"本地图片：{len(local_images)} 张",
            f"网络图片：{len(network_urls)} 张",
            "",
            "本地图片列表：",
        ]
        lines.extend([f"- {os.path.basename(path)}" for path in local_images[:10]] or ["- 暂无"])
        if network_urls:
            lines.extend(["", "网络图片："])
            lines.extend([f"- {url}" for url in network_urls[:5]])
        return "\n".join(lines)

    def build_image_preview_visual(self):
        local_images, network_urls = self.prepare_shared_images()
        heading = f"将发送 {len(local_images) + len(network_urls)} 张图片"
        desc = "发送顺序与资源池顺序一致。可使用右侧“上移 / 下移”调整图片顺序。"
        badges = [
            (f"本地 {len(local_images)}", "#e8f1fb", self.COLOR_PRIMARY),
            (f"网络 {len(network_urls)}", "#fff7e6", "#8a6d00"),
        ]
        sections = [
            ("发送顺序", "拖拽列表或使用上移 / 下移后，这里的发送顺序会立即生效。"),
            ("首张图片", os.path.basename(local_images[0]) if local_images else (network_urls[0] if network_urls else "暂无图片")),
        ]
        return ("图片批量发送", heading, desc, badges, sections)

    def build_news_preview_text(self):
        lines = [
            "模式：单图文消息",
            f"标题：{self.news_title_entry.get().strip() or '未填写'}",
            f"描述：{self.news_desc_entry.get().strip() or '未填写'}",
            f"跳转：{self.news_url_entry.get().strip() or '未填写'}",
            f"封面：{self.news_picurl_entry.get().strip() or '将自动从共享图片区推断'}",
            "",
            "说明：图文消息只稳定支持单封面，多余图片会在发送后补发。",
        ]
        return "\n".join(lines)

    def build_news_preview_visual(self):
        heading = self.news_title_entry.get().strip() or "未填写图文标题"
        desc = self.news_desc_entry.get().strip() or "这里会展示图文消息的描述摘要。"
        has_cover = bool(self.news_picurl_entry.get().strip() or self.image_paths or self.get_network_image_urls())
        badges = [
            ("单图文", "#e8f1fb", self.COLOR_PRIMARY),
            ("有封面" if has_cover else "无封面", "#eef7ee" if has_cover else "#fff1f2", self.COLOR_SUCCESS if has_cover else self.COLOR_ERROR),
        ]
        sections = [
            ("跳转链接", self.news_url_entry.get().strip() or "未填写"),
            ("封面来源", self.news_picurl_entry.get().strip() or "将从共享图片区自动推断"),
        ]
        return ("图文消息预览", heading, desc, badges, sections)

    def build_template_preview_text(self):
        vertical_count = sum(1 for row in self.vertical_rows if row["title"].get().strip() or row["desc"].get().strip())
        horizontal_count = sum(1 for row in self.horizontal_rows if row["key"].get().strip() and row["value"].get().strip())
        jump_count = sum(1 for row in self.jump_rows if row["url"].get().strip() and row["title"].get().strip())
        lines = [
            "模式：图文卡片",
            f"主标题：{self.card_title_entry.get().strip() or '未填写'}",
            f"主描述：{self.card_desc_entry.get().strip() or '未填写'}",
            f"头图：{self.card_image_entry.get().strip() or '将自动推断'}",
            f"图文区标题：{self.card_image_area_title_entry.get().strip() or '未填写'}",
            f"图文区图片：{self.card_image_area_url_entry.get().strip() or '将自动推断'}",
            f"垂直内容数：{vertical_count}",
            f"水平内容数：{horizontal_count}",
            f"跳转按钮数：{jump_count}",
            "",
            "提示：图文卡片多余图片会在发送后补发，不会全部塞进卡片结构。",
        ]
        return "\n".join(lines)

    def build_template_preview_visual(self):
        vertical_count = sum(1 for row in self.vertical_rows if row["title"].get().strip() or row["desc"].get().strip())
        horizontal_count = sum(1 for row in self.horizontal_rows if row["key"].get().strip() and row["value"].get().strip())
        jump_count = sum(1 for row in self.jump_rows if row["url"].get().strip() and row["title"].get().strip())
        heading = self.card_title_entry.get().strip() or "未填写卡片主标题"
        desc = self.card_desc_entry.get().strip() or "卡片主描述会显示在这里。"
        badges = [
            (f"垂直 {vertical_count}", "#e8f1fb", self.COLOR_PRIMARY),
            (f"水平 {horizontal_count}", "#eef7ee", self.COLOR_SUCCESS),
            (f"跳转 {jump_count}", "#fff7e6", "#8a6d00"),
        ]
        sections = [
            ("头图", self.card_image_entry.get().strip() or "将自动推断头图"),
            ("图文区", self.card_image_area_title_entry.get().strip() or "未填写图文区标题"),
            ("结构统计", f"垂直 {vertical_count} 项，水平 {horizontal_count} 项，跳转 {jump_count} 项"),
        ]
        return ("图文卡片预览", heading, desc, badges, sections)

    def refresh_live_preview(self):
        current = self.msg_type_var.get()
        if current == "Markdown":
            self.set_preview_text("Markdown", self.build_markdown_preview_text())
            self.set_preview_visual(*self.build_markdown_preview_visual())
            return
        if current == "图片":
            self.set_preview_text("图片", self.build_image_preview_text())
            self.set_preview_visual(*self.build_image_preview_visual())
            return
        if current == "图文消息":
            self.set_preview_text("图文消息", self.build_news_preview_text())
            self.set_preview_visual(*self.build_news_preview_visual())
            return
        if current == "图文卡片":
            self.set_preview_text("图文卡片", self.build_template_preview_text())
            self.set_preview_visual(*self.build_template_preview_visual())

    def move_selected_images(self, direction):
        indices = list(self.image_listbox.curselection())
        if not indices:
            return
        if direction < 0 and indices[0] == 0:
            return
        if direction > 0 and indices[-1] == len(self.image_paths) - 1:
            return

        if direction < 0:
            for index in indices:
                self.image_paths[index - 1], self.image_paths[index] = self.image_paths[index], self.image_paths[index - 1]
            new_selection = [index - 1 for index in indices]
        else:
            for index in reversed(indices):
                self.image_paths[index + 1], self.image_paths[index] = self.image_paths[index], self.image_paths[index + 1]
            new_selection = [index + 1 for index in indices]

        self.refresh_image_list()
        for index in new_selection:
            self.image_listbox.selection_set(index)
        self.set_status("状态：已调整图片顺序", self.COLOR_SUCCESS, auto_reset=True)

    def on_image_listbox_press(self, event):
        self.dragging_image_index = self.image_listbox.nearest(event.y)

    def on_image_listbox_drag(self, event):
        if self.dragging_image_index is None or not self.image_paths:
            return
        target_index = self.image_listbox.nearest(event.y)
        if target_index == self.dragging_image_index or target_index < 0 or target_index >= len(self.image_paths):
            return
        item = self.image_paths.pop(self.dragging_image_index)
        self.image_paths.insert(target_index, item)
        self.dragging_image_index = target_index
        self.refresh_image_list()
        self.image_listbox.selection_clear(0, tk.END)
        self.image_listbox.selection_set(target_index)

    def on_image_listbox_release(self, _event):
        if self.dragging_image_index is not None:
            self.set_status("状态：已拖拽调整图片顺序", self.COLOR_SUCCESS, auto_reset=True)
        self.dragging_image_index = None

    def remove_selected_images(self):
        selected_indices = list(self.image_listbox.curselection())
        if not selected_indices:
            return
        for index in reversed(selected_indices):
            self.image_paths.pop(index)
        self.refresh_image_list()
        self.set_status("状态：已移除选中图片", self.COLOR_SUCCESS, auto_reset=True)

    def clear_images(self):
        self.image_paths.clear()
        self.refresh_image_list()
        self.net_image_text.delete("1.0", tk.END)
        self.set_status("状态：共享图片区已清空", self.COLOR_SUCCESS, auto_reset=True)

    def get_network_image_urls(self):
        raw_text = self.net_image_text.get("1.0", tk.END)
        urls = []
        seen = set()
        for line in raw_text.splitlines():
            url = line.strip()
            if not url:
                continue
            if url not in seen:
                urls.append(url)
                seen.add(url)
        return urls

    def get_mentioned_mobiles(self):
        values = []
        seen = set()
        raw = self.at_entry.get().strip()
        if raw:
            for item in re.split(r"[,;\s]+", raw):
                phone = item.strip()
                if phone and phone not in seen and phone != "all":
                    values.append(phone)
                    seen.add(phone)
        return values

    def register_temp_file(self, path):
        if path:
            self.temp_files.add(path)
        return path

    def cleanup_temp_files(self):
        for path in list(self.temp_files):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
            finally:
                self.temp_files.discard(path)

    def compress_image(self, image_path, max_size_mb=2):
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        if file_size_mb <= max_size_mb:
            return image_path

        with Image.open(image_path) as image:
            original_width, original_height = image.size
            ratio = min(1.0, (max_size_mb * 1024 * 1024 / max(os.path.getsize(image_path), 1)) ** 0.5)
            width = max(200, int(original_width * ratio))
            height = max(200, int(original_height * ratio))
            resample = getattr(Image, "Resampling", Image).LANCZOS
            resized = image.resize((width, height), resample)

            suffix = os.path.splitext(image_path)[1] or ".jpg"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.close()
            output_path = self.register_temp_file(temp_file.name)

            save_kwargs = {"optimize": True}
            ext = suffix.lower()
            if ext in {".jpg", ".jpeg", ".webp"}:
                if resized.mode not in ("RGB", "L"):
                    resized = resized.convert("RGB")
                save_kwargs["quality"] = 82
            resized.save(output_path, **save_kwargs)
            return output_path

    def download_image(self, url):
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        suffix = os.path.splitext(url.split("?")[0])[1] or ".jpg"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(response.content)
        temp_file.flush()
        temp_file.close()
        return self.register_temp_file(temp_file.name)

    def build_image_payload(self, image_path):
        compressed = self.compress_image(image_path, max_size_mb=2)
        with open(compressed, "rb") as file:
            image_bytes = file.read()
        return {"msgtype": "image", "image": {"base64": base64.b64encode(image_bytes).decode("utf-8"), "md5": hashlib.md5(image_bytes).hexdigest()}}

    def upload_image_to_free_host(self, image_path):
        compressed = self.compress_image(image_path, max_size_mb=2)
        with open(compressed, "rb") as file:
            image_data = file.read()

        mime_type, _ = mimetypes.guess_type(compressed)
        if not mime_type:
            mime_type = "application/octet-stream"

        files = {"file": (os.path.basename(compressed), image_data, mime_type)}
        data = {"fileName": os.path.basename(compressed), "uid": "3dfd757677824cecadcd7640baeb787d"}
        headers = {"accept": "application/json, text/plain, */*", "user-agent": "Mozilla/5.0"}

        response = requests.post("https://imgbed.cn/img/upload", files=files, data=data, headers=headers, timeout=40)
        response.raise_for_status()
        result = response.json()
        image_url = result.get("url")
        if not image_url:
            raise Exception(f"图床响应异常：{result}")
        return image_url

    def post_payload(self, webhook_url, payload):
        response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        response.raise_for_status()
        result = response.json()
        if result.get("errcode") != 0:
            raise Exception(f"企微接口错误：{result.get('errmsg')}（错误码：{result.get('errcode')}）")

    def prepare_shared_images(self):
        return list(self.image_paths), self.get_network_image_urls()

    def build_markdown_bundle(self):
        content = self.markdown_text.get("1.0", tk.END).strip()
        if not content:
            raise Exception("请输入 Markdown 内容。")

        local_images, network_urls = self.prepare_shared_images()
        mentioned = self.get_mentioned_mobiles()
        extra_images = []
        notes = []

        if self.at_all_var.get():
            content += "\n<@all>"
        for phone in mentioned:
            content += f"\n<@{phone}>"

        embedded_urls = list(network_urls)
        if local_images:
            if self.local_image_mode_var.get() == "图床转URL":
                self.set_status("状态：正在上传 Markdown 图片...", self.COLOR_WARNING)
                for image_path in local_images:
                    embedded_urls.append(self.upload_image_to_free_host(image_path))
            else:
                extra_images = [self.build_image_payload(path) for path in local_images]
                notes.append("本地图片按“直接发送”模式处理，将在 Markdown 后逐张补发。")

        for index, url in enumerate(embedded_urls, start=1):
            content += f"\n\n![图片{index}]({url})"

        payload = {"msgtype": "markdown", "markdown": {"content": content}, "mentioned_mobile_list": mentioned}
        return {"primary": payload, "extra_images": extra_images, "notes": notes}

    def build_image_bundle(self):
        local_images, network_urls = self.prepare_shared_images()
        image_payloads = [self.build_image_payload(path) for path in local_images]
        for url in network_urls:
            downloaded = self.download_image(url)
            image_payloads.append(self.build_image_payload(downloaded))

        if not image_payloads:
            raise Exception("请至少选择一张本地图片，或输入一条网络图片 URL。")

        return {"primary": None, "extra_images": image_payloads, "notes": []}

    def build_news_bundle(self):
        title = self.news_title_entry.get().strip()
        description = self.news_desc_entry.get().strip()
        url = self.news_url_entry.get().strip()
        explicit_picurl = self.news_picurl_entry.get().strip()
        if not title:
            raise Exception("图文消息标题不能为空。")
        if not url:
            raise Exception("图文消息跳转链接不能为空。")

        local_images, network_urls = self.prepare_shared_images()
        extra_images = []
        notes = []
        picurl = explicit_picurl
        consumed_network = 0
        consumed_local = 0

        if not picurl and network_urls:
            picurl = network_urls[0]
            consumed_network = 1
        elif not picurl and local_images and self.local_image_mode_var.get() == "图床转URL":
            picurl = self.upload_image_to_free_host(local_images[0])
            consumed_local = 1

        for image_path in local_images[consumed_local:]:
            extra_images.append(self.build_image_payload(image_path))
        for image_url in network_urls[consumed_network:]:
            extra_images.append(self.build_image_payload(self.download_image(image_url)))

        if extra_images:
            notes.append("图文消息只支持单张封面图，额外图片会在图文消息后继续补发。")

        article = {"title": title, "description": description, "url": url}
        if picurl:
            article["picurl"] = picurl

        payload = {"msgtype": "news", "news": {"articles": [article]}}
        return {"primary": payload, "extra_images": extra_images, "notes": notes}

    def build_template_bundle(self):
        title = self.card_title_entry.get().strip()
        if not title:
            raise Exception("图文卡片主标题不能为空。")

        description = self.card_desc_entry.get().strip()
        card_image_url = self.card_image_entry.get().strip()
        image_area_title = self.card_image_area_title_entry.get().strip()
        image_area_desc = self.card_image_area_desc_entry.get().strip()
        image_area_url = self.card_image_area_url_entry.get().strip()
        image_area_jump = self.card_image_area_jump_entry.get().strip()

        local_images, network_urls = self.prepare_shared_images()
        shared_urls = list(network_urls)
        notes = []
        extra_images = []

        if self.local_image_mode_var.get() == "图床转URL":
            for path in local_images:
                shared_urls.append(self.upload_image_to_free_host(path))
        else:
            for path in local_images:
                extra_images.append(self.build_image_payload(path))

        if not card_image_url:
            if shared_urls:
                card_image_url = shared_urls.pop(0)
            else:
                card_image_url = DEFAULT_CARD_IMAGE_URL

        if not image_area_url and shared_urls:
            image_area_url = shared_urls.pop(0)

        for url in shared_urls:
            extra_images.append(self.build_image_payload(self.download_image(url)))

        if extra_images:
            notes.append("企微图文卡片稳定支持的图片位有限，额外图片会在卡片后继续补发。")

        payload = {
            "msgtype": "template_card",
            "template_card": {
                "card_type": "news_notice",
                "main_title": {"title": title},
                "card_image": {"url": card_image_url, "aspect_ratio": 2.25},
                "vertical_content_list": [],
                "horizontal_content_list": [],
                "jump_list": [],
                "card_action": {"type": 1, "url": image_area_jump or "https://work.weixin.qq.com", "title": "查看详情"},
            },
        }

        if description:
            payload["template_card"]["main_title"]["desc"] = description

        if image_area_url:
            payload["template_card"]["image_text_area"] = {"image_url": image_area_url, "type": 1, "url": image_area_jump or "https://work.weixin.qq.com"}
            if image_area_title:
                payload["template_card"]["image_text_area"]["title"] = image_area_title
            if image_area_desc:
                payload["template_card"]["image_text_area"]["desc"] = image_area_desc

        vertical_items = []
        for row in self.vertical_rows:
            title_value = row["title"].get().strip()
            desc_value = row["desc"].get().strip()
            if title_value or desc_value:
                item = {}
                if title_value:
                    item["title"] = title_value
                if desc_value:
                    item["desc"] = desc_value
                vertical_items.append(item)
        if vertical_items:
            payload["template_card"]["vertical_content_list"] = vertical_items

        horizontal_items = []
        for row in self.horizontal_rows:
            key_value = row["key"].get().strip()
            value_value = row["value"].get().strip()
            if key_value and value_value:
                horizontal_items.append({"keyname": key_value, "value": value_value})
        if horizontal_items:
            payload["template_card"]["horizontal_content_list"] = horizontal_items

        jump_items = []
        for row in self.jump_rows:
            jump_type = row["type"].get()
            jump_url = row["url"].get().strip()
            jump_title = row["title"].get().strip()
            if jump_url and jump_title:
                jump_items.append({"type": jump_type, "url": jump_url, "title": jump_title})
        if jump_items:
            payload["template_card"]["jump_list"] = jump_items
            payload["template_card"]["card_action"] = jump_items[0]

        return {"primary": payload, "extra_images": extra_images, "notes": notes}

    def add_vertical_row(self, title="", desc=""):
        row_frame = ttk.Frame(self.vertical_rows_container, style="Surface.TFrame")
        row_frame.pack(fill=tk.X, pady=6)
        row_frame.columnconfigure(1, weight=1)
        row_frame.columnconfigure(3, weight=1)

        ttk.Label(row_frame, text="标题", style="Body.TLabel").grid(row=0, column=0, sticky=tk.W)
        title_entry = ttk.Entry(row_frame)
        title_entry.grid(row=0, column=1, sticky=tk.EW, padx=(8, 12))
        title_entry.insert(0, title)

        ttk.Label(row_frame, text="描述", style="Body.TLabel").grid(row=0, column=2, sticky=tk.W)
        desc_entry = ttk.Entry(row_frame)
        desc_entry.grid(row=0, column=3, sticky=tk.EW, padx=(8, 12))
        desc_entry.insert(0, desc)
        title_entry.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())
        desc_entry.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())

        ttk.Button(row_frame, text="删除", style="Danger.TButton", command=lambda: self.remove_vertical_row(row_frame)).grid(row=0, column=4)
        self.vertical_rows.append({"frame": row_frame, "title": title_entry, "desc": desc_entry})

    def remove_vertical_row(self, row_frame):
        self.vertical_rows = [row for row in self.vertical_rows if row["frame"] != row_frame]
        row_frame.destroy()
        self.schedule_preview_refresh()

    def add_horizontal_row(self, keyname="", value=""):
        row_frame = ttk.Frame(self.horizontal_rows_container, style="Surface.TFrame")
        row_frame.pack(fill=tk.X, pady=6)
        row_frame.columnconfigure(1, weight=1)
        row_frame.columnconfigure(3, weight=1)

        ttk.Label(row_frame, text="标题", style="Body.TLabel").grid(row=0, column=0, sticky=tk.W)
        key_entry = ttk.Entry(row_frame)
        key_entry.grid(row=0, column=1, sticky=tk.EW, padx=(8, 12))
        key_entry.insert(0, keyname)

        ttk.Label(row_frame, text="内容", style="Body.TLabel").grid(row=0, column=2, sticky=tk.W)
        value_entry = ttk.Entry(row_frame)
        value_entry.grid(row=0, column=3, sticky=tk.EW, padx=(8, 12))
        value_entry.insert(0, value)
        key_entry.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())
        value_entry.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())

        ttk.Button(row_frame, text="删除", style="Danger.TButton", command=lambda: self.remove_horizontal_row(row_frame)).grid(row=0, column=4)
        self.horizontal_rows.append({"frame": row_frame, "key": key_entry, "value": value_entry})

    def remove_horizontal_row(self, row_frame):
        self.horizontal_rows = [row for row in self.horizontal_rows if row["frame"] != row_frame]
        row_frame.destroy()
        self.schedule_preview_refresh()

    def add_jump_row(self, jump_type=1, url="", title=""):
        row_frame = ttk.Frame(self.jump_rows_container, style="Surface.TFrame")
        row_frame.pack(fill=tk.X, pady=6)
        row_frame.columnconfigure(3, weight=1)
        row_frame.columnconfigure(5, weight=1)

        ttk.Label(row_frame, text="类型", style="Body.TLabel").grid(row=0, column=0, sticky=tk.W)
        type_var = tk.IntVar(value=jump_type)
        type_box = ttk.Combobox(row_frame, textvariable=type_var, values=[1, 2], state="readonly", width=6)
        type_box.grid(row=0, column=1, sticky=tk.W, padx=(8, 12))

        ttk.Label(row_frame, text="URL", style="Body.TLabel").grid(row=0, column=2, sticky=tk.W)
        url_entry = ttk.Entry(row_frame)
        url_entry.grid(row=0, column=3, sticky=tk.EW, padx=(8, 12))
        url_entry.insert(0, url)

        ttk.Label(row_frame, text="标题", style="Body.TLabel").grid(row=0, column=4, sticky=tk.W)
        title_entry = ttk.Entry(row_frame)
        title_entry.grid(row=0, column=5, sticky=tk.EW, padx=(8, 12))
        title_entry.insert(0, title)
        url_entry.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())
        title_entry.bind("<KeyRelease>", lambda _event: self.schedule_preview_refresh())
        type_var.trace_add("write", lambda *_args: self.schedule_preview_refresh())

        ttk.Button(row_frame, text="删除", style="Danger.TButton", command=lambda: self.remove_jump_row(row_frame)).grid(row=0, column=6)
        self.jump_rows.append({"frame": row_frame, "type": type_var, "url": url_entry, "title": title_entry})

    def remove_jump_row(self, row_frame):
        self.jump_rows = [row for row in self.jump_rows if row["frame"] != row_frame]
        row_frame.destroy()
        self.schedule_preview_refresh()

    def build_message_bundle(self):
        msg_type = self.msg_type_var.get()
        if msg_type == "图片":
            return self.build_image_bundle()
        if msg_type == "Markdown":
            return self.build_markdown_bundle()
        if msg_type == "图文消息":
            return self.build_news_bundle()
        if msg_type == "图文卡片":
            return self.build_template_bundle()
        raise Exception(f"不支持的消息类型：{msg_type}")

    def send_message(self):
        selected_webhooks = self.get_selected_webhooks()
        if not selected_webhooks:
            messagebox.showinfo("提示", "请先选择至少一个 Webhook。")
            return

        self.send_btn.state(["disabled"])
        self.set_status(f"状态：正在准备发送到 {len(selected_webhooks)} 个 Webhook ...", self.COLOR_WARNING)

        def worker():
            success_count = 0
            fail_details = []
            notes = []
            try:
                bundle = self.build_message_bundle()
                notes.extend(bundle.get("notes", []))

                for index, webhook_name in enumerate(selected_webhooks, start=1):
                    self.set_status(f"状态：正在发送第 {index}/{len(selected_webhooks)} 个 Webhook（{webhook_name}）...", self.COLOR_WARNING)
                    try:
                        webhook_url = self.webhooks[webhook_name]
                        if bundle.get("primary"):
                            self.post_payload(webhook_url, bundle["primary"])
                        for image_payload in bundle.get("extra_images", []):
                            self.post_payload(webhook_url, image_payload)
                        success_count += 1
                    except Exception as error:
                        fail_details.append(f"{webhook_name}：{error}")

                result_lines = [f"成功：{success_count} 个", f"失败：{len(fail_details)} 个"]
                if notes:
                    result_lines.append("")
                    result_lines.extend(notes)
                if fail_details:
                    result_lines.append("")
                    result_lines.append("失败详情：")
                    result_lines.extend(fail_details)

                self.set_status("状态：消息发送完成", self.COLOR_SUCCESS, auto_reset=True)
                if fail_details:
                    self.root.after(0, lambda: messagebox.showwarning("发送结果", "\n".join(result_lines)))
                else:
                    self.root.after(0, lambda: messagebox.showinfo("发送成功", "\n".join(result_lines)))
            except Exception as error:
                self.set_status(f"状态：发送失败 - {error}", self.COLOR_ERROR, auto_reset=True)
                self.root.after(0, lambda: messagebox.showerror("发送失败", str(error)))
            finally:
                self.cleanup_temp_files()
                self.root.after(0, lambda: self.send_btn.state(["!disabled"]))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap("icon.ico")
    except Exception:
        pass
    app = WeChatRobotSender(root)
    root.mainloop()