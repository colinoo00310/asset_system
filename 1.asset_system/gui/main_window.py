"""
主窗口模块
混合架构：使用 Tkinter GUI，但通过 PyQt5 启动
"""

import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

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

from utils.utils import Utils


class MainWindow:
    """主窗口（基于 Tkinter）"""

    _first_show = True

    def __init__(self, root, db, auth):
        self.root = root
        self.db = db
        self.auth = auth
        self.utils = Utils()

        self.root.title("XXX公司 资产管理系统")
        self.root.geometry("1200x800")
        self.root.minsize(1200, 800)
        self.root.resizable(False, False)

        self.show_main_interface()

        # 防止主窗口被缩小
        self._configure_binding_id = None
        self._rebind_configure()

    def _rebind_configure(self):
        """重新绑定 Configure 事件"""
        if self._configure_binding_id is not None:
            try:
                self.root.unbind("<Configure>")
            except Exception:
                pass

        self._initial_geometry = "1200x800"

        def _enforce_geometry(event=None):
            if event and event.widget != self.root:
                return
            self.root.update()
            w, h = self.root.winfo_width(), self.root.winfo_height()
            if w != 1200 or h != 800:
                x, y = self.root.winfo_x(), self.root.winfo_y()
                self.root.geometry(f"1200x800+{x}+{y}")
                self.root.update()

        self._configure_binding_id = self.root.bind("<Configure>", _enforce_geometry)

    def show_main_interface(self):
        """显示主界面"""
        for widget in self.root.winfo_children():
            widget.destroy()

        if MainWindow._first_show:
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - 1200) // 2
            y = (screen_height - 800) // 2
            self.root.geometry(f"1200x800+{x}+{y}")
            MainWindow._first_show = False

        self.create_navigation_bar()

        self.main_content = tk.Frame(self.root)
        self.main_content.pack(side="left", fill="both", expand=True)

        self.show_home_page()

    def create_navigation_bar(self):
        """创建左侧导航栏"""
        nav_frame = tk.Frame(self.root, width=200, bg="#2c3e50")
        nav_frame.pack(side="left", fill="y")
        nav_frame.pack_propagate(False)

        title_label = tk.Label(nav_frame, text="资产管理系统", bg="#2c3e50", fg="white",
                               font=('微软雅黑', 14, 'bold'), padx=10, pady=15)
        title_label.pack(fill="x")

        menu_container = tk.Frame(nav_frame, bg="#2c3e50")
        menu_container.pack(fill="x")

        menu_items = [
            ("🏠", "系统首页", None, lambda: self.show_home_page()),
            ("🗺️", "地图展示", None, lambda: self.show_map_view()),
            ("📊", "信息管理", "▼", [
                ("资产管理", lambda: self.show_asset_management()),
                ("部门管理", lambda: self.show_department_management()),
                ("用户管理", lambda: self.show_user_management())
            ]),
            ("❓", "帮助", None, lambda: self.show_about())
        ]

        icon_width = 3

        for item in menu_items:
            icon, text, arrow, payload = item[0], item[1], item[2], item[3]
            if isinstance(payload, list):
                self.create_submenu(menu_container, icon, text, arrow, payload, icon_width)
            else:
                self.create_nav_button(menu_container, icon, text, payload, icon_width)

        spacer = tk.Frame(nav_frame, bg="#2c3e50", height=0)
        spacer.pack(fill="x", expand=True)

        switch_frame = tk.Frame(nav_frame, bg="#34495e")
        switch_frame.pack(fill="x", side="bottom")

        switch_btn = tk.Button(switch_frame, text="🔄 切换账号", command=self.switch_account,
                               bg="#e74c3c", fg="white", bd=0, padx=20, pady=12,
                               activebackground="#c0392b", font=('微软雅黑', 12, 'bold'))
        switch_btn.pack(fill="x", expand=True)

    def create_nav_button(self, parent, icon, text, command, icon_width):
        """创建单个导航按钮"""
        row = tk.Frame(parent, bg="#2c3e50")
        row.pack(fill="x")
        icon_label = tk.Label(row, text=icon, bg="#2c3e50", fg="white",
                              font=('微软雅黑', 12), width=icon_width, anchor="w")
        icon_label.pack(side="left", padx=(20, 0), pady=10)
        btn = tk.Button(row, text=text, command=command,
                        bg="#2c3e50", fg="white", bd=0, padx=0, pady=10,
                        anchor="w", font=('微软雅黑', 12))
        btn.pack(side="left", fill="x", expand=True)
        icon_label.bind("<Button-1>", lambda e: command())

    def create_submenu(self, parent, icon, text, arrow, items, icon_width):
        """创建子菜单"""
        main_frame = tk.Frame(parent, bg="#2c3e50")
        main_frame.pack(fill="x")

        btn_frame = tk.Frame(main_frame, bg="#2c3e50")
        btn_frame.pack(fill="x")

        icon_label = tk.Label(btn_frame, text=icon, bg="#2c3e50", fg="white",
                              font=('微软雅黑', 12), width=icon_width, anchor="w")
        icon_label.pack(side="left", padx=(20, 0), pady=10)
        btn = tk.Button(btn_frame, text=text, bg="#2c3e50", fg="white", bd=0,
                        padx=0, pady=10, anchor="w", font=('微软雅黑', 12))
        btn.pack(side="left", fill="x", expand=True)

        arrow_label = tk.Label(btn_frame, text=arrow, bg="#2c3e50", fg="white", font=('微软雅黑', 10))
        arrow_label.pack(side="right", padx=10)

        submenu_frame = tk.Frame(main_frame, bg="#34495e")
        submenu_visible = False

        def toggle_submenu():
            nonlocal submenu_visible
            if submenu_visible:
                submenu_frame.pack_forget()
                arrow_label.config(text="▼")
            else:
                submenu_frame.pack(fill="x")
                arrow_label.config(text="▲")
            submenu_visible = not submenu_visible

        btn.config(command=toggle_submenu)
        icon_label.bind("<Button-1>", lambda e: toggle_submenu())
        arrow_label.bind("<Button-1>", lambda e: toggle_submenu())

        for text, command in items:
            sub_btn = tk.Button(submenu_frame, text=f"  {text}", command=command,
                                bg="#34495e", fg="white", bd=0, padx=30, pady=8,
                                anchor="w", font=('微软雅黑', 11))
            sub_btn.pack(fill="x")

    def show_home_page(self):
        """显示系统首页"""
        from gui.home import HomePage
        HomePage(self.main_content, self.db, self.auth)

    def show_asset_management(self):
        """显示资产管理"""
        from gui.assets import AssetManagement
        AssetManagement(self.main_content, self.db, self.auth)

    def show_department_management(self):
        """显示部门管理"""
        from gui.departments import DepartmentManagement
        DepartmentManagement(self.main_content, self.db, self.auth)

    def show_user_management(self):
        """显示用户管理"""
        from gui.users import UserManagement
        UserManagement(self.main_content, self.db, self.auth)

    def show_map_view(self):
        """显示地图展示"""
        import subprocess
        import sys
        import tempfile
        import json
        import time
        import traceback
        import ctypes
        from ctypes import wintypes

        def get_short_path_name(long_path):
            """将长路径转换为短路径（8.3格式）"""
            try:
                GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
                GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
                GetShortPathNameW.restype = wintypes.DWORD
                buffer_size = GetShortPathNameW(long_path, None, 0)
                if buffer_size == 0:
                    return long_path
                buffer = ctypes.create_unicode_buffer(buffer_size)
                result = GetShortPathNameW(long_path, buffer, buffer_size)
                if result > 0:
                    return buffer.value
                return long_path
            except Exception:
                return long_path

        self.root.update_idletasks()
        self._saved_geometry = self.root.geometry()

        try:
            # 准备参数
            db_path = os.path.abspath(self.db.db_file)
            current_user = self.auth.get_current_user()
            auth_data = {
                'logged_in': True,
                'user': current_user,
                'permissions': self.auth.user_permissions
            }

            temp_dir = tempfile.gettempdir()
            param_file = os.path.join(temp_dir, "map_launch_params.json")

            params = {
                'db_path': db_path,
                'auth_data': auth_data
            }

            with open(param_file, 'w', encoding='utf-8') as f:
                json.dump(params, f)

            from tkinter import messagebox

            # 确定启动方式和目标
            if getattr(sys, 'frozen', False):
                # 打包环境：使用当前 exe
                exe_path = sys.executable
                exe_dir = os.path.dirname(exe_path)
                project_dir = exe_dir

                # 确保路径安全（处理中文路径）
                exe_path_safe = get_short_path_name(exe_path)
                param_file_safe = get_short_path_name(param_file)
                project_dir_safe = get_short_path_name(project_dir)

                target = [exe_path_safe, '--map-mode', param_file_safe]

                # 创建日志文件记录子进程输出
                log_file = os.path.join(temp_dir, "map_child_output.log")

                try:
                    with open(log_file, 'w', encoding='utf-8') as logf:
                        # 启动子进程，捕获输出
                        process = subprocess.Popen(
                            target,
                            cwd=project_dir_safe,
                            stdout=logf,
                            stderr=subprocess.STDOUT
                        )

                    # 等待一小段时间让子进程启动
                    time.sleep(2)

                    # 检查进程是否还在运行
                    poll_result = process.poll()
                    if poll_result is None:
                        messagebox.showinfo("成功", f"地图进程已启动 (PID: {process.pid})")
                    else:
                        # 进程已退出，读取日志
                        try:
                            with open(log_file, 'r', encoding='utf-8') as logf:
                                output = logf.read()
                            messagebox.showerror("进程退出", f"地图进程退出，代码: {poll_result}\n\n输出:\n{output[:2000]}")
                        except:
                            messagebox.showerror("进程退出", f"地图进程退出，代码: {poll_result}")
                except Exception as e:
                    messagebox.showerror("启动失败", f"启动地图进程失败:\n{str(e)}")
            else:
                # 开发环境
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_dir = os.path.dirname(os.path.dirname(script_dir))
                map_script = os.path.join(script_dir, "map", "map_standalone.py")
                target = [sys.executable, map_script, param_file]

                process = subprocess.Popen(
                    target,
                    cwd=project_dir
                )

                messagebox.showinfo("成功", f"地图进程已启动 (PID: {process.pid})")

        except Exception as e:
            error_msg = f"启动地图失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERROR] {error_msg}")
            from tkinter import messagebox
            messagebox.showerror("错误", f"启动地图失败:\n{str(e)}")

    def _restore_main_window(self):
        """恢复主窗口"""
        self.root.state('normal')
        self.root.update()
        for _ in range(3):
            self.root.geometry("1200x800")
            self.root.update()
        self._rebind_configure()

    def show_about(self):
        """显示关于"""
        messagebox.showinfo("关于", "XXX公司 资产管理系统V1.0版本\n\n功能：\n- 资产管理\n- 部门管理\n- 用户管理\n 版本更新时间：XX年X月X日")

    def switch_account(self):
        """切换账号"""
        if messagebox.askyesno("切换账号", "确定要切换账号吗？"):
            from gui.login import LoginWindow
            LoginWindow(self.root)
