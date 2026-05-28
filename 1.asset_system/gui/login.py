"""
登录界面模块
基于 Tkinter
"""

import os
import sys

# 添加项目根目录到路径（兼容开发和打包环境）
def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        else:
            return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

project_root = get_project_root()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import tkinter as tk
from tkinter import ttk, messagebox


class LoginWindow:
    """登录窗口（基于 Tkinter）"""

    def __init__(self, root):
        self.root = root
        self.root.title("XXX公司 资产管理系统")
        self.root.geometry("1200x800")

        # 导入模块
        from config.database import Database
        from services.auth import AuthManager
        from utils.utils import Utils

        self.db = Database()
        self.auth = AuthManager(self.db)
        self.utils = Utils()

        self.captcha_answer, self.captcha_text = self.utils.generate_captcha()
        self.show_login()

    def show_login(self):
        """显示登录界面"""
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 1200
        window_height = 800
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 背景图片
        image_path = self.utils.resource_path("images/login-background.png")
        try:
            if os.path.exists(image_path):
                from PIL import Image, ImageTk
                img = Image.open(image_path)
                img = img.resize((1200, 800), Image.LANCZOS)
                self.bg_image = ImageTk.PhotoImage(img)

                bg_label = tk.Label(self.root, image=self.bg_image)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.root.configure(bg="#f0f0f0")
        except Exception as e:
            self.root.configure(bg="#f0f0f0")

        # 登录框
        login_frame = tk.Frame(self.root, bg="white", bd=2, relief="groove")
        login_frame.place(relx=0.5, rely=0.5, anchor="center", width=400)

        # 标题
        title_frame = tk.Frame(login_frame, bg="#2c3e50", height=70)
        title_frame.pack(fill="x")

        tk.Label(title_frame, text="XXX有限公司资产管理系统",
                 font=('微软雅黑', 15, 'bold'), bg="#2c3e50", fg="white").pack(pady=(10, 5))

        # 表单区域
        form_frame = tk.Frame(login_frame, bg="white", padx=20, pady=20)
        form_frame.pack()

        # 用户名
        tk.Label(form_frame, text="用户名:", bg="white", font=('微软雅黑', 10)).grid(row=0, column=0, pady=5,
                                                                                     sticky="e")
        self.username_entry = ttk.Entry(form_frame, width=25, font=('微软雅黑', 10))
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)

        # 密码
        tk.Label(form_frame, text="密码:", bg="white", font=('微软雅黑', 10)).grid(row=1, column=0, pady=5, sticky="e")
        self.password_entry = ttk.Entry(form_frame, width=25, show="*", font=('微软雅黑', 10))
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)

        # 验证码
        captcha_frame = tk.Frame(form_frame, bg="white")
        captcha_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

        tk.Label(captcha_frame, text="验证码:", bg="white", font=('微软雅黑', 10)).pack(side="left")

        self.captcha_entry = ttk.Entry(captcha_frame, width=8, font=('微软雅黑', 9), style='Round.TEntry')
        self.captcha_entry.pack(side="left", padx=10)

        self.captcha_display = tk.Frame(captcha_frame, bg="#f5f5f5", relief="groove", bd=1, padx=10, pady=3)
        self.captcha_display.pack(side="left", padx=5)

        self.captcha_label = tk.Label(self.captcha_display, text=self.captcha_text,
                                      font=('微软雅黑', 10, 'bold'), bg="#f5f5f5", fg="#333333")
        self.captcha_label.pack()

        refresh_btn = tk.Button(captcha_frame, text="↻", command=self.generate_captcha,
                                font=('微软雅黑', 9), bd=0, bg="#e9e9e9", activebackground="#d9d9d9", relief="flat",
                                padx=5)
        refresh_btn.pack(side="left", padx=5)

        # 登录按钮
        login_btn = tk.Button(form_frame, text="登录", command=self.do_login,
                              bg="#3498db", fg="white", font=('微软雅黑', 10, 'bold'),
                              bd=0, padx=20, pady=5, activebackground="#2980b9")
        login_btn.grid(row=4, column=0, columnspan=2, pady=15)

        # 底部文字
        footer_label = tk.Label(self.root, text="XXX有限公司XXX部门承办",
                                font=('微软雅黑', 10), fg="white", bg="#2c3e50")
        footer_label.place(relx=0.5, rely=0.97, anchor="center")

        # 设置焦点和回车键绑定
        self.username_entry.focus_set()
        self.root.bind('<Return>', lambda event: self.do_login(event))

    def generate_captcha(self):
        """生成验证码"""
        self.captcha_answer, self.captcha_text = self.utils.generate_captcha()
        if hasattr(self, 'captcha_label'):
            self.captcha_label.config(text=self.captcha_text)

    def do_login(self, event=None):
        """执行登录操作"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        captcha_input = self.captcha_entry.get().strip()

        if not username or not password:
            messagebox.showerror("错误", "用户名和密码不能为空")
            return

        # 验证验证码
        try:
            if int(captcha_input) != self.captcha_answer:
                messagebox.showerror("错误", "验证码错误")
                self.generate_captcha()
                return
        except ValueError:
            messagebox.showerror("错误", "验证码必须是数字")
            self.generate_captcha()
            return

        if self.auth.login(username, password):
            self.root.unbind('<Return>')
            from gui.main_window import MainWindow
            MainWindow(self.root, self.db, self.auth)
        else:
            messagebox.showerror("错误", "用户名或密码不正确")
            self.generate_captcha()
