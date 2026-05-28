import os
import sys
import random


class Utils:
    @staticmethod
    def resource_path(relative_path):
        """获取资源的绝对路径，兼容开发环境和打包后环境"""
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

        path = os.path.join(base_path, relative_path)
        return os.path.normpath(path)

    @staticmethod
    def center_window(window):
        """将窗口居中显示"""
        window.update_idletasks()

        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window_width = window.winfo_width()
        window_height = window.winfo_height()

        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        window.geometry(f"+{x}+{y}")

    @staticmethod
    def center_window_on_parent(window, parent):
        """将窗口在父窗口中央显示"""
        window.update_idletasks()

        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        window_width = window.winfo_width()
        window_height = window.winfo_height()

        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2

        window.geometry(f"+{x}+{y}")

    @staticmethod
    def generate_captcha():
        """生成验证码算式"""
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        return a + b, f"{a} + {b} = ?"

    @staticmethod
    def validate_number(value):
        """验证数字输入"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_float(value):
        """验证浮点数输入"""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_image_path(db_path, db_file=None):
        """获取有效的图片绝对路径"""
        if not db_path or str(db_path) == "未选择图片":
            return None

        # 兼容开发和打包环境
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                project_root = sys._MEIPASS
            else:
                project_root = os.path.dirname(sys.executable)
        else:
            project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

        possible_paths = [
            db_path,
            os.path.join(project_root, "assets", "images", os.path.basename(db_path)),
            os.path.join(project_root, "images", os.path.basename(db_path)),
            os.path.join(os.path.dirname(db_file or os.path.join(project_root, "main.py")), os.path.basename(db_path)),
            os.path.join(os.getcwd(), os.path.basename(db_path)),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None
